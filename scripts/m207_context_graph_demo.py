#!/usr/bin/env python3
"""Понятный прототип: граф документа и два способа взять контекст.

Это НЕ парсер продукта, НЕ золото, НЕ порт Pullenti.
Это модель «как устроен документ» на живых кусках seed M199.

Запуск:
  uv run python scripts/m207_context_graph_demo.py
  uv run python scripts/m207_context_graph_demo.py --doc npa-doc-020
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "prd/migration/rust-evidence/m199-s01-gold-sample-manifest.json"
FIX = ROOT / "crates/ln-decode/tests/fixtures/npa-lawref"
TYPE_LEXICON = ROOT / "prd/architecture/npa-identifying-cycle.yaml"
AXES_PATH = ROOT / "prd/architecture/npa-classification-axes.yaml"

OT_DATE = re.compile(
    r"(?<!вх\.\s)(?<!вх\s)от\s+(\d{2}\.\d{2}\.\d{4})\s+"
    r"(?:N\s+([0-9А-ЯA-Z]+(?:[./-][0-9А-ЯA-Z]+)*)|(б/н))",
    re.I,
)
# «от 29 июля 2017 года N 218-ФЗ» — дата Думы в теле, не только в шапке XML.
OT_DUMA = re.compile(
    r"(?<!вх\.\s)от\s+(\d{1,2})\s+([а-яё]+)\s+(\d{4})\s+г(?:ода|\.)\s+N\s+"
    r"([0-9А-ЯA-Z]+(?:[./-][0-9А-ЯA-Z]+)*)",
    re.I,
)
UKAZANNY = re.compile(
    r"указанн\w*\s+Федеральн\w*\s+закон\w*",
    re.I,
)
# «правовой позиции Конституционного суда …, изложенной в пункте 4 Постановления от …» —
# эмитент вынесен из оборота; тип переносим только внутри этого узкого клише.
CTX_CARRY = re.compile(
    r"(Конституционного суда|Пленума Верховного Суда|Верховного Суда|антимонопольного органа)"
    r"[^.]{0,200}?изложенн\w+\s+в\s+[^.]{0,60}?"
    r"(Постановлени\w+|Определени\w+)\s+от\s+(\d{2}\.\d{2}\.\d{4})\s+N\s+"
    r"([0-9А-ЯA-Z][0-9А-ЯA-Z/н\-.]*)",
    re.I,
)


def _ctx_carry_type(issuer: str, kind_word: str) -> str | None:
    fold = issuer.casefold()
    act = "Постановление" if kind_word[:4].casefold() == "пост" else "Определение"
    if "конституционного" in fold:
        return f"{act} КС РФ"
    if "пленума" in fold:
        return f"{act} Пленума ВС РФ" if act == "Постановление" else None
    if "верховного" in fold:
        return f"{act} ВС РФ"
    if "антимонопольного" in fold:
        return "Решение УФАС России"
    return None
INBOUND = re.compile(
    r"\(вх\.\s*(?:от\s+\d{2}\.\d{2}\.\d{4}\s+N\s+[0-9А-ЯA-Z/-]+"
    r"|N\s+[0-9А-ЯA-Z/-]+\s+от\s+\d{2}\.\d{2}\.\d{4})",
    re.I,
)
# D385 scoped_alias: «далее — …». Не CurrentDocumentRequisites (тот sidecar — только этот XML).
DALEE = re.compile(r"\(далее\s*[-\u2014]\s*([^)]+)\)", re.I)
SHORT_LAW_N = re.compile(
    r"(Закон\w*|Постановлен\w*|Приказ\w*|Указ\w*)"
    r"\s+N\s+([0-9А-ЯA-Z]+(?:[/-][0-9А-ЯA-Z]+)*)",
    re.I,
)
THIS_REF = re.compile(
    r"настоящ\w*\s+(Положен\w*|Правил\w*|Федеральн\w*\s+закон\w*|Кодекс\w*)",
    re.I,
)
_PARTY_ALIAS = re.compile(
    r"^(заявитель|истец|ответчик|оператор|организатор|продажа|еис)$",
    re.I,
)
# Порядок важен: КС раньше Правительства; письмо раньше жалобы (часто в одном абзаце).
TYPE_HEAD = re.compile(
    r"(Постановлен\w*\s+Конституционн\w*\s+Суд\w*\s+(?:РФ|Российск\w*\s+Федераци\w*)|"
    r"Постановлен\w*\s+КС\s+РФ|"
    r"постановлен\w*\s+Пленума\s+Верховн\w*\s+Суд\w*\s+(?:РФ|Российск\w*\s+Федераци\w*)|"
    r"постановлен\w*\s+Пленума\s+ВАС\s+РФ|"
    r"Конституционн\w*\s+Суд\w*(?:\s+Российск\w*\s+Федераци\w*)?\s+в\s+Постановлен\w*|"
    r"Указ\w*\s+Президента\s+(?:РФ|Российск\w*\s+Федераци\w*)|"
    r"Постановлен\w*\s+Правительства\s+(?:РФ|Российск\w*\s+Федераци\w*)|"
    r"распоряжен\w*\s+Правительства\s+(?:РФ|Российск\w*\s+Федераци\w*)|"
    r"Приказ\w*(?:\s+(?!от\b)(?-i:[А-ЯЁA-Z])[А-ЯЁа-яёA-Za-z\-]*(?:\s+(?!от\b|об\b|о\b|не\b)(?!(?-i:Министерств|Федеральн|Государственн|Совет|Фонд|Палат|Агентств|Служб|Главн))(?![а-яё]+(?:ущ|ющ|ащ|ящ|вш)\w*)[А-ЯЁа-яёA-Za-z\-]+)*)*|"
    r"письм(?:о|а|у|ом|е|ам|ами|ах)\b(?:\s+(?!от\b)(?-i:[А-ЯЁA-Z])[А-ЯЁа-яёA-Za-z\-]*(?:\s+(?!от\b|об\b|о\b|не\b)(?!(?-i:Министерств|Федеральн|Государственн|Совет|Фонд|Палат|Агентств|Служб|Главн))(?![а-яё]+(?:ущ|ющ|ащ|ящ|вш)\w*)[А-ЯЁа-яёA-Za-z\-]+)*)*|"
    r"распоряжен\w*\s+Президента\s+(?:РФ|Российск\w*\s+Федераци\w*)|"
    r"распоряжен\w*(?:\s+(?!от\b)(?!об\s+услови)(?-i:[А-ЯЁA-Z])[А-ЯЁа-яёA-Za-z\-]*(?:\s+(?!от\b|об\b|о\b|не\b)(?!(?-i:Министерств|Федеральн|Государственн|Совет|Фонд|Палат|Агентств|Служб|Главн))(?![а-яё]+(?:ущ|ющ|ащ|ящ|вш)\w*)[А-ЯЁа-яёA-Za-z\-]+)*)*|"
    r"Федеральн\w*\s+конституционн\w*\s+закон\w*|"
    r"(?<![-\w])ФЗ(?!\w)|"
    r"Федеральн\w+\s+закон\w*|"
    r"Закон\w*\s+СССР|"
    r"Закон\w*\s+Российск\w*\s+Федераци\w*|"
    r"Трудов\w*\s+кодекс\w*|"
    r"Таможенн\w*\s+кодекс\w*|"
    r"Гражданск\w*\s+процессуальн\w*\s+кодекс\w*|"
    r"Уголовно-процессуальн\w*\s+кодекс\w*|"
    r"Арбитражн\w*\s+процессуальн\w*\s+кодекс\w*|"
    r"Кодекс\w*\s+административн\w*\s+судопроизводств\w*|"
    r"Налогов\w*\s+кодекс\w*|"
    r"Бюджетн\w*\s+кодекс\w*|"
    r"Земельн\w*\s+кодекс\w*|"
    r"Жилищн\w*\s+кодекс\w*|"
    r"Семейн\w*\s+кодекс\w*|"
    r"Лесн\w*\s+кодекс\w*|"
    r"Гражданск\w*\s+кодекс\w*|"
    r"Уголовно-исполнительн\w*\s+кодекс\w*|"
    r"Уголовн\w*\s+кодекс\w*|"
    r"(?<!\w)КоАП(?:\s+РФ)?(?!\w)|"
    r"(?<!\w)АПК(?:\s+РФ)?(?!\w)|"
    r"(?<!\w)ГПК(?:\s+РФ)?(?!\w)|"
    r"(?<!\w)УПК(?:\s+РФ)?(?!\w)|"
    r"(?<!\w)КАС(?:\s+РФ)?(?!\w)|"
    r"(?<!\w)УИК(?:\s+РФ)?(?!\w)|"
    r"(?<!\w)ГК\s+РФ(?!\w)|"
    r"(?<!\w)УК\s+РФ(?!\w)|"
    r"(?<!\w)НК\s+РФ(?!\w)|"
    r"(?<!\w)БК\s+РФ(?!\w)|"
    r"(?<!\w)ЗК\s+РФ(?!\w)|"
    r"(?<!\w)ЖК\s+РФ(?!\w)|"
    r"(?<!\w)СК\s+РФ(?!\w)|"
    r"(?<!\w)ЛК\s+РФ(?!\w)|"
    r"решени\w*\s+антимонопольн\w*\s+орган\w*|"
    r"постановлен\w*\s+антимонопольн\w*\s+орган\w*|"
    r"решени\w*(?:\s+(?!от\b)(?!(?-i:Министерств|Федеральн|Государственн|Совет|Фонд|Палат|Агентств|Служб|Главн))(?-i:[А-ЯЁA-Z])[А-ЯЁа-яёA-Za-z\-]*(?:\s+(?!от\b|об\b|о\b|не\b)(?!(?-i:Министерств|Федеральн|Государственн|Совет|Фонд|Палат|Агентств|Служб|Главн))(?![а-яё]+(?:ущ|ющ|ащ|ящ|вш)\w*)[А-ЯЁа-яёA-Za-z\-]+)*)*(?:УФАС|ФАС)(?:\s+(?!от\b)(?!(?-i:Министерств|Федеральн|Государственн|Совет|Фонд|Палат|Агентств|Служб|Главн))(?-i:[А-ЯЁA-Z])[А-ЯЁа-яёA-Za-z\-]*(?:\s+(?!от\b|об\b|о\b|не\b)(?!(?-i:Министерств|Федеральн|Государственн|Совет|Фонд|Палат|Агентств|Служб|Главн))(?![а-яё]+(?:ущ|ющ|ащ|ящ|вш)\w*)[А-ЯЁа-яёA-Za-z\-]+)*)*|"
    r"Положен\w*\s+о[б]?\s|"
    r"Правил\w*\s+(?:осуществления|проведения|подготовки|применения|использования|формирования|государственной|ведения)|"
    r"договор\w*[^.]{0,60}?\s+от|"
    r"запрос\w*\s+от|"
    r"акт\w*\s+приема-передачи|"
    r"акт\w*\s+проверк\w*|"
    r"свидетельств\w*\s+о\s+рождении|"
    r"претензи\w*|"
    r"платежн\w*\s+поручени\w*|"
    r"протокол\w*|"
    r"доверенност\w*|"
    r"(?<!в\s)жалоб\w*|"
    r"лицензи\w*|"
    r"соглашен\w*|"
    r"контракт(?:а|у|ом|е)?\s+от|"
    r"извещен\w*|"
    r"Методическ\w*\s+рекомендац\w*|"
    r"Регламент\w*\s+(?:торгов\w*|универсальн\w*|размещения)|"
    r"техническ\w*\s+регламент\w*|"
    r"(?<!\w)ТР\s+(?:ТС|ЕАЭС)(?!\w)|"
    r"(?<!\w)ГОСТ(?:\s+Р)?(?!\w)|"
    r"(?<!\w)(?:ИСО|ISO|IEC)(?!\w)|"
    r"(?<!\w)СНиП(?!\w)|"
    r"(?<!\w)СанПиН(?!\w)|"
    r"Дополнительн\w*\s+требован\w*\s+к\s|"
    r"Конкурсн\w*\s+документац\w*|"
    r"перечн\w*\s+(?:товаров|работ)|"
    r"Порядк\w*\s+(?:подготовки|проведения|оказания|определения))",
    re.I,
)
_MINJUST = re.compile(
    r"Зарегистрировано\s+в\s+Минюсте\s+России\s+"
    r"(?:"
    r"(?P<dmy>\d{2}\.\d{2}\.\d{4})"
    r"|"
    r"(?P<day>\d{1,2})\s+(?P<mon>[а-яё]+)\s+(?P<year>\d{4})\s+г(?:ода|\.)?"
    r")\s+N\s+(?P<num>\d+)",
    re.I,
)
ED_NOTE = re.compile(r"^\s*\(в\s+ред\.", re.I)
IZM_NOTE = re.compile(r"^\s*с\s+изм\.,\s+внесенными", re.I)
# Pullenti DecreePart: ст./ч./п. на кодексе. Диагностика, не идентичность акта.
_ART_NUM = r"[\d.]+(?:-[\d]+)?"
_ART_LIST = _ART_NUM + r"(?:\s*(?:[-–—,]|и)\s*" + _ART_NUM + r")*"
CODE_PART = re.compile(
    r"(?:(?P<pk>ч(?:аст\w*)?|п(?:ункт\w*)?)\.?\s*"
    r"(?P<part>" + _ART_LIST + r")\s+)?"
    r"(?:ст\.?|стат\w*)\s+"
    r"(?P<article>" + _ART_LIST + r")"
    r"(?:\s+(?P<code>КоАП|АПК|ГПК|УПК|КАС|УИК|ГК|УК|НК|БК)\s*РФ)?",
    re.I,
)
# Правка «дополнить частями/пунктами X–Y» без «статьи» — диагностика, не акт.
CODE_PART_BARE = re.compile(
    r"(?P<pk>част\w*|пункт\w*)\s+(?P<part>" + _ART_LIST + r")",
    re.I,
)
_ISO_STD = re.compile(
    r"(?<!\w)(?P<fam>"
    r"техническ\w*\s+регламент\w*(?:\s+(?:таможенн\w*\s+союза|еаэс))?"
    r"|ТР\s+(?:ТС|ЕАЭС)"
    r"|ГОСТ(?:\s+Р)?"
    r"|ИСО|ISO|IEC"
    r"|СНиП|СанПиН"
    r"|СП(?!\w)"
    r")\s*(?P<num>[\d][\d./\-]*(?::\d{4})?)",
    re.I,
)
# Закупки / медицина / рег.номера юрлица — не TYPE и не член. Голый ТР ⊄ «третье».
# КТРУ = каталог ТРУ; правила утв. пост. Правительства РФ от 08.02.2017 N 145 (не сам каталог — акт).
_NOT_ACT = re.compile(
    r"(?<!\w)("
    r"ЕИС|ИНН|ОГРН|КПП|НМЦК|НМЦ|КТРУ|ОКПД2?|ОКВЭД|"
    r"МНН|ЖНВЛП|ЖНВЛС|ОНЛС|ФОМС|ОМС|ДМС|СНИЛС|"
    r"ЕГРЮЛ|ЕГРИП|ЭТП"
    r")(?!\w)",
    re.I,
)
_KTRU = re.compile(
    r"(?<!\w)КТРУ(?!\w)|каталог\w*\s+товаров,\s+работ,\s+услуг",
    re.I,
)
_EIS = re.compile(
    r"(?<!\w)ЕИС(?!\w)|единой\s+информационн\w*\s+систем\w*\s+в\s+сфере\s+закупок",
    re.I,
)
# Платформа / каталог → утверждающий акт. Не 44-ФЗ: 44-ФЗ задаёт обязанность, не систему.
_PLATFORM_ACT = {
    "КТРУ": ("08.02.2017", "145", "Постановление Правительства РФ"),
    "ЕИС": ("27.01.2022", "60", "Постановление Правительства РФ"),
}
_NOT_ACT_WHY = {
    "КТРУ": "каталог ТРУ — не акт; правила формирования и использования утв. пост. Правительства РФ от 08.02.2017 N 145",
    "ЕИС": "единая информационная система закупок — платформа, не акт; информационное обеспечение утв. пост. Правительства РФ от 27.01.2022 N 60 (не 44-ФЗ)",
    "ИНН": "рег.номер юрлица, не акт",
    "ОГРН": "рег.номер юрлица, не акт",
    "КПП": "рег.номер юрлица, не акт",
    "НМЦК": "начальная (максимальная) цена контракта — параметр закупки, не акт",
    "НМЦ": "начальная (максимальная) цена — параметр закупки, не акт",
    "ОКПД": "классификатор продукции, не акт",
    "ОКПД2": "классификатор продукции, не акт",
    "ОКВЭД": "классификатор видов деятельности, не акт",
    "МНН": "международное непатентованное наименование ЛП, не акт",
    "ЖНВЛП": "перечень ЖНВЛП — не акт без утверждающего постановления",
    "ЖНВЛС": "перечень ЖНВЛС — не акт без утверждающего постановления",
    "ОНЛС": "программа обеспечения ЛС, не акт",
    "ФОМС": "фонд ОМС — орган/плательщик, не акт",
    "ОМС": "обязательное медстрахование, не акт",
    "ДМС": "добровольное медстрахование, не акт",
    "СНИЛС": "рег.номер физлица, не акт",
    "ЕГРЮЛ": "реестр юрлиц, не акт",
    "ЕГРИП": "реестр ИП, не акт",
    "ЭТП": "электронная торговая площадка, не акт",
}
_DUMA_HEAD = re.compile(
    r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})\s+г(?:ода|\.)\s+N\s+"
    r"([0-9А-ЯA-Z]+(?:[./-][0-9А-ЯA-Z]+)*)",
    re.I,
)
_MONTHS_RU = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
}
_CORP_ACTOR = re.compile(r"\b(?:ООО|АО|ПАО|ИП|ЗАО)\b")

# Именительный ед.ч. слота TYPE (как Pullenti ATTR_TYPE), не падеж фразы «в ред. Указов».
KIND_CANON = (
    (
        re.compile(r"^федеральн\w*\s+конституционн\w*\s+закон\w*$", re.I),
        "Федеральный конституционный закон",
    ),
    (re.compile(r"^федеральн\w*\s+закон\w*$", re.I), "Федеральный закон"),
    (re.compile(r"^фз$", re.I), "Федеральный закон"),
    (re.compile(r"^закон\w*\s+российск\w*\s+федераци\w*$", re.I), "Закон РФ"),
    (re.compile(r"^закон\w*\s+ссср$", re.I), "Закон СССР"),
    (re.compile(r"^указ\w*\s+президента\s+рф$", re.I), "Указ Президента РФ"),
    (re.compile(r"^указ\w*\s+президента\s+российск\w*\s+федераци\w*$", re.I), "Указ Президента РФ"),
    (re.compile(r"^распоряжен\w*\s+президента\s+(?:рф|российск\w*\s+федераци\w*)$", re.I), "Распоряжение Президента РФ"),
    (re.compile(r"^постановлен\w*\s+правительства\s+(?:рф|российск\w*\s+федераци\w*)$", re.I), "Постановление Правительства РФ"),
    (re.compile(r"^распоряжен\w*\s+правительства\s+(?:рф|российск\w*\s+федераци\w*)$", re.I), "распоряжение Правительства РФ"),
    (re.compile(r"^постановлен\w*\s+конституционн\w*\s+суда\s+рф$", re.I), "Постановление КС РФ"),
    (re.compile(r"^постановлен\w*\s+конституционн\w*\s+суд\w*\s+российск\w*\s+федераци\w*$", re.I), "Постановление КС РФ"),
    (re.compile(r"^постановлен\w*\s+кс\s+рф$", re.I), "Постановление КС РФ"),
    (
        re.compile(
            r"^конституционн\w*\s+суд\w*(?:\s+российск\w*\s+федераци\w*)?\s+в\s+постановлен\w*$",
            re.I,
        ),
        "Постановление КС РФ",
    ),
    (
        re.compile(r"^постановлен\w*\s+пленума\s+верховн\w*\s+суда\s+рф$", re.I),
        "Постановление Пленума ВС РФ",
    ),
    (
        re.compile(r"^постановлен\w*\s+пленума\s+верховн\w*\s+суд\w*\s+российск\w*\s+федераци\w*$", re.I),
        "Постановление Пленума ВС РФ",
    ),
    (
        re.compile(r"^решени\w*\s+антимонопольн\w*\s+орган\w*$", re.I),
        "Решение УФАС России",
    ),
    (
        re.compile(r"^постановлен\w*\s+пленума\s+вас\s+рф$", re.I),
        "Постановление Пленума ВАС РФ",
    ),
    (re.compile(r"^коап(?:\s+рф)?$", re.I), "КоАП РФ"),
    (re.compile(r"^апк(?:\s+рф)?$", re.I), "АПК РФ"),
    (re.compile(r"^гпк(?:\s+рф)?$", re.I), "ГПК РФ"),
    (re.compile(r"^упк(?:\s+рф)?$", re.I), "УПК РФ"),
    (re.compile(r"^кас(?:\s+рф)?$", re.I), "КАС РФ"),
    (re.compile(r"^нк(?:\s+рф)?$", re.I), "НК РФ"),
    (re.compile(r"^бк(?:\s+рф)?$", re.I), "БК РФ"),
    (re.compile(r"^зк(?:\s+рф)?$", re.I), "ЗК РФ"),
    (re.compile(r"^жк(?:\s+рф)?$", re.I), "ЖК РФ"),
    (re.compile(r"^ск(?:\s+рф)?$", re.I), "СК РФ"),
    (re.compile(r"^лк(?:\s+рф)?$", re.I), "ЛК РФ"),
    (re.compile(r"^гражданск\w*\s+процессуальн\w*\s+кодекс\w*$", re.I), "ГПК РФ"),
    (re.compile(r"^уголовно-процессуальн\w*\s+кодекс\w*$", re.I), "УПК РФ"),
    (re.compile(r"^арбитражн\w*\s+процессуальн\w*\s+кодекс\w*$", re.I), "АПК РФ"),
    (re.compile(r"^кодекс\w*\s+административн\w*\s+судопроизводств\w*$", re.I), "КАС РФ"),
    (re.compile(r"^налогов\w*\s+кодекс\w*$", re.I), "НК РФ"),
    (re.compile(r"^бюджетн\w*\s+кодекс\w*$", re.I), "БК РФ"),
    (re.compile(r"^земельн\w*\s+кодекс\w*$", re.I), "ЗК РФ"),
    (re.compile(r"^жилищн\w*\s+кодекс\w*$", re.I), "ЖК РФ"),
    (re.compile(r"^семейн\w*\s+кодекс\w*$", re.I), "СК РФ"),
    (re.compile(r"^лесн\w*\s+кодекс\w*$", re.I), "ЛК РФ"),
    (
        re.compile(
            r"^кодекс\w*\s+российск\w*\s+федераци\w*\s+об\s+административн",
            re.I,
        ),
        "КоАП РФ",
    ),
    (re.compile(r"^трудов\w*\s+кодекс\w*$", re.I), "Трудовой кодекс"),
    (re.compile(r"^таможенн\w*\s+кодекс\w*$", re.I), "Таможенный кодекс"),
    (re.compile(r"^гражданск\w*\s+кодекс\w*$", re.I), "Гражданский кодекс"),
    (re.compile(r"^гк\s+рф$", re.I), "Гражданский кодекс"),
    (re.compile(r"^уголовно-исполнительн\w*\s+кодекс\w*$", re.I), "Уголовно-исполнительный кодекс"),
    (re.compile(r"^уик\s+рф$", re.I), "Уголовно-исполнительный кодекс"),
    (re.compile(r"^уголовн\w*\s+кодекс\w*$", re.I), "Уголовный кодекс"),
    (re.compile(r"^ук\s+рф$", re.I), "Уголовный кодекс"),
    (re.compile(r"^положен\w*(?:\s+о[б]?.*)?$", re.I), "положение"),
    (re.compile(r"^правил\w*(?:\s+.*)?$", re.I), "правила"),
    (re.compile(r"^договор\w*$", re.I), "договор"),
    (re.compile(r"^запрос\w*$", re.I), "запрос"),
    (re.compile(r"^акт\w*\s+приема-передачи$", re.I), "акт приема-передачи"),
    (re.compile(r"^акт\w*\s+проверк\w*$", re.I), "акт проверки"),
    (re.compile(r"^свидетельств\w*\s+о\s+рождени\w*$", re.I), "свидетельство о рождении"),
    (re.compile(r"^претензи\w*$", re.I), "претензия"),
    (re.compile(r"^платежн\w*\s+поручени\w*$", re.I), "платежное поручение"),
    (re.compile(r"^конкурсн\w*\s+документац\w*$", re.I), "конкурсная документация"),
    (re.compile(r"^дополнительн\w*\s+требован\w*", re.I), "требования"),
    (re.compile(r"^перечн\w*", re.I), "перечень"),
    (re.compile(r"^порядк\w*", re.I), "порядок"),
    (re.compile(r"^методическ\w*\s+рекомендац\w*", re.I), "методические рекомендации"),
    (re.compile(r"^регламент\w*", re.I), "регламент"),
    (re.compile(r"^(приказ\w*)\s+(.+)$", re.I), None),  # ствол Приказ + издатель как написан
    (re.compile(r"^(письм\w*)\s+(.+)$", re.I), None),  # ствол Письмо + издатель как написан
    (re.compile(r"^(распоряжен\w*)\s+(.+)$", re.I), None),  # после «распоряжение Правительства»
    (re.compile(r"^(решени\w*)\s+(.+)$", re.I), None),  # решение УФАС/ФАС, не голое «решение»
    (re.compile(r"^доверенност\w*$", re.I), "доверенность"),
    (re.compile(r"^жалоб\w*$", re.I), "жалоба"),
    (re.compile(r"^лицензи\w*$", re.I), "лицензия"),
    (re.compile(r"^соглашен\w*$", re.I), "соглашение"),
    (re.compile(r"^контракт\w*$", re.I), "контракт"),
    (re.compile(r"^извещен\w*$", re.I), "извещение"),
    (re.compile(r"^протокол\w*$", re.I), "протокол"),
)


def canon_act_type(written: str) -> str:
    """Слот TYPE = именительный ед.ч. Текст абзаца не трогаем."""
    folded = re.sub(r"\s+", " ", written).strip()
    std = _ISO_STD.search(folded)
    if std:
        fam = re.sub(r"\s+", " ", std.group("fam")).strip()
        fl = fam.casefold()
        num = std.group("num") or ""
        if "регламент" in fl:
            fam_up = "технический регламент"
        elif "еаэс" in fl:
            fam_up = "ТР ЕАЭС"
        elif fl.startswith("тр"):
            fam_up = "ТР ТС"
        elif re.search(r"гост\s+р", fl):
            fam_up = "ГОСТ Р"
        elif fl.startswith("гост"):
            fam_up = "ГОСТ"
        elif fl in {"iso", "изо"} or fl.startswith("изо"):
            fam_up = "ИСО"
        elif fl == "iec":
            fam_up = "IEC"
        elif fl.startswith("снип"):
            fam_up = "СНиП"
        elif fl.startswith("санпин"):
            fam_up = "СанПиН"
        elif fl == "сп":
            fam_up = "СП"
        else:
            fam_up = fam
        return f"{fam_up} {num}".strip()
    for pattern, canon in KIND_CANON:
        hit = pattern.match(folded)
        if not hit:
            continue
        if canon is not None:
            return canon
        stem = hit.group(1).casefold()
        issuer = hit.group(2).strip(" ,")
        if stem.startswith("письм"):
            blank = "Письмо"
        elif stem.startswith("распоряжен"):
            blank = "Распоряжение"
        elif stem.startswith("решени"):
            blank = "Решение"
        else:
            blank = "Приказ"
        return f"{blank} {issuer}" if issuer else blank
    return folded


def load_type_lexicon(path: Path) -> dict[str, object]:
    """Закрытый список лемм TYPE из identifying-cycle. Второй словарь не заводим."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    lemmas = data.get("act_type_lemmas") or {}
    skip = {str(x).casefold() for x in lemmas.get("skip_as_type") or []}
    instrument = {str(x).casefold() for x in lemmas.get("instrument") or []}
    identifying: dict[str, str] = {}
    for bucket, names in lemmas.items():
        if bucket in {"skip_as_type", "instrument", "named"}:
            continue
        for name in names or []:
            identifying[str(name).casefold()] = str(bucket)
    named = {str(x).casefold() for x in lemmas.get("named") or []}
    return {
        "identifying": identifying,
        "skip": skip,
        "instrument": instrument,
        "named": named,
        "raw": lemmas,
    }


_LEXICON: dict[str, object] | None = None


def lexicon() -> dict[str, object]:
    global _LEXICON
    if _LEXICON is None:
        _LEXICON = load_type_lexicon(TYPE_LEXICON)
    return _LEXICON


# Форма (ось A) больше не равна ребру в граф НПА. agency=приказ+письмо — склеенный
# bucket identifying-cycle; решение ребра берёт classify_layers (D516).


# Окончание словоизменения, не новая основа. «ание» у «указание» сюда не входит.
_INFLECT = {
    "",
    "а",
    "у",
    "е",
    "ом",
    "ем",
    "ов",
    "ам",
    "ами",
    "ах",
    "ы",
    "и",
    "й",
    "я",
    "ю",
    "ей",
    "ий",
    "ие",
    "ия",
    "ием",
    "иям",
    "иями",
    "иях",
    "ое",
    "ая",
    "ые",
    "ого",
    "ому",
    "ым",
    "ых",
    "ыми",
}
_STEMS = (
    "постановление",
    "распоряжение",
    "доверенность",
    "соглашение",
    "извещение",
    "указание",
    "лицензия",
    "положение",
    "контракт",
    "протокол",
    "приказ",
    "письмо",
    "жалоба",
    "кодекс",
    "коап",
    "апк",
    "указ",
    "закон",
)
_STEM_ALIAS = {
    "коап": "кодекс",
    "апк": "кодекс",
    "гпк": "кодекс",
    "упк": "кодекс",
    "кас": "кодекс",
    "уик": "кодекс",
    "гк": "кодекс",
    "ук": "кодекс",
    "нк": "кодекс",
    "бк": "кодекс",
    "зк": "кодекс",
    "жк": "кодекс",
    "ск": "кодекс",
    "лк": "кодекс",
}
# Pullenti DecreeToken Termin+Acronym, KIND=Kodex (RU). Ориентация, не runtime.
# Голый ТК/ВК — омограф (труд/таможня; вода/воздух) — fail-closed без полного имени. Не копируем UA.
CODE_ABBREV = (
    ("КОАП", "КоАП РФ", "Кодекс об административных правонарушениях"),
    ("АПК", "АПК РФ", "Арбитражный процессуальный кодекс"),
    ("ГПК", "ГПК РФ", "Гражданский процессуальный кодекс"),
    ("УПК", "УПК РФ", "Уголовно-процессуальный кодекс"),
    ("КАС", "КАС РФ", "Кодекс административного судопроизводства"),
    ("УИК", "Уголовно-исполнительный кодекс", "Уголовно-исполнительный кодекс"),
    ("ГК", "Гражданский кодекс", "Гражданский кодекс"),
    ("УК", "Уголовный кодекс", "Уголовный кодекс"),
    ("НК", "НК РФ", "Налоговый кодекс"),
    ("БК", "БК РФ", "Бюджетный кодекс"),
    ("ЗК", "ЗК РФ", "Земельный кодекс"),
    ("ЖК", "ЖК РФ", "Жилищный кодекс"),
    ("СК", "СК РФ", "Семейный кодекс"),
    ("ЛК", "ЛК РФ", "Лесной кодекс"),
)
_CODE_ABBREV_CANONS = {row[1].casefold() for row in CODE_ABBREV}
_CODE_ABBREV_STEMS = tuple(sorted({row[0].casefold() for row in CODE_ABBREV}, key=len, reverse=True))
_CODE_ABBREV_CANONS = {row[1].casefold() for row in CODE_ABBREV}
# Два разных закона о закупках. Не омограф номера. 223-ФЗ в seed нет — dest не выдумываем.
PROCUREMENT_LAW = (
    ("44-ФЗ", "05.04.2013", "Федеральный закон",
     "О контрактной системе в сфере закупок товаров, работ, услуг для обеспечения государственных и муниципальных нужд"),
    ("223-ФЗ", "18.07.2011", "Федеральный закон",
     "О закупках товаров, работ, услуг отдельными видами юридических лиц"),
)
_PROCURE_TITLE = re.compile(
    r"(?:Федеральн\w*\s+закон\w*\s+)?\"?О\s+контрактной\s+системе"
    r"|о\s+закупках\s+товаров,\s+работ,\s+услуг\s+отдельными\s+видами",
    re.I,
)


def lemma_match(written: str, key: str) -> bool:
    """Точное или словоизменение. Не «указ» ⊂ «указание»."""
    a, b = written.casefold(), key.casefold()
    if a == b:
        return True
    if a.startswith(b) and a[len(b) :] in _INFLECT:
        return True
    if b.startswith(a) and b[len(a) :] in _INFLECT:
        return True
    return False


def stem_kind(canon: str) -> str:
    folded = re.sub(r"\s+", " ", canon).strip().casefold()
    if folded.startswith("федеральн"):
        return "закон"
    if re.search(
        r"(трудов\w*|таможенн\w*|гражданск\w*|уголовно-исполнительн\w*|"
        r"уголовно-процессуальн\w*|уголовн\w*|арбитражн\w*|налогов\w*|"
        r"бюджетн\w*|земельн\w*|жилищн\w*|семейн\w*|лесн\w*)\s+кодекс",
        folded,
    ) or "процессуальн" in folded and "кодекс" in folded:
        return "кодекс"
    if folded in {"тк", "тк рф", "вк", "вк рф"}:
        return "тк"  # омограф; не кодекс без полного имени
    for stem in _CODE_ABBREV_STEMS:
        if folded == stem or folded.startswith(stem + " ") or folded.startswith(stem + "рф") or folded == stem + " рф":
            return "кодекс"
    if folded in _CODE_ABBREV_CANONS:
        return "кодекс"
    first = folded.split()[0]
    for key in sorted(_STEMS, key=len, reverse=True):
        if lemma_match(first, key):
            return _STEM_ALIAS.get(key, key)
    return first


def classify_type(canon: str | None, lexicon: dict[str, object]) -> dict[str, str]:
    """Сверка слота TYPE со словарём. Не в граф идентичности — если отклонение."""
    if not canon:
        return {
            "lemma": "",
            "bucket": "",
            "verdict": "type_missing",
            "graph": "refuse",
            "why": "нет типа — ребро в граф актов не строим (иначе появится узел «неизвестно N 446»)",
        }
    lemma = stem_kind(canon)
    identifying: dict[str, str] = lexicon["identifying"]  # type: ignore[assignment]
    skip: set[str] = lexicon["skip"]  # type: ignore[assignment]
    instrument: set[str] = lexicon["instrument"]  # type: ignore[assignment]
    named: set[str] = lexicon["named"]  # type: ignore[assignment]
    folded = lemma.casefold()

    def _hits(key: str) -> bool:
        return lemma_match(folded, key)

    candidates: list[tuple[int, int, str, str]] = []
    for key in skip:
        if _hits(key):
            candidates.append((1 if folded == key else 0, len(key), "skip", key))
    for key in instrument:
        if _hits(key):
            candidates.append((1 if folded == key else 0, len(key), "instrument", key))
    for key in named:
        if _hits(key):
            candidates.append((1 if folded == key else 0, len(key), "named", key))
    for key, bucket in identifying.items():
        if _hits(key):
            candidates.append((1 if folded == key else 0, len(key), bucket, key))
    if re.search(r"документац", folded) or re.search(
        r"конкурсн\w*\s+документац", (canon or "").casefold()
    ):
        return {
            "lemma": "документация",
            "bucket": "named",
            "verdict": "named_annex",
            "graph": "hold",
            "why": (
                "конкурсная документация — named annex утверждающего приказа, "
                "не отдельный акт и не TYPE приказа"
            ),
        }
    if re.search(r"рекомендац", folded) or re.search(
        r"рекомендац", (canon or "").casefold()
    ):
        return {
            "lemma": "рекомендации",
            "bucket": "named",
            "verdict": "named_annex",
            "graph": "hold",
            "why": (
                "методические рекомендации — named annex утверждающего приказа, "
                "свой DATE+N нет"
            ),
        }
    if folded.startswith("регламент"):
        return {
            "lemma": "регламент",
            "bucket": "named",
            "verdict": "named_annex",
            "graph": "hold",
            "why": (
                "регламент торговой площадки — named annex; "
                "корпоративный гендиректор ≠ ФОИВ"
            ),
        }
    if folded.startswith("переч") or folded.startswith("поряд"):
        return {
            "lemma": "перечень" if folded.startswith("переч") else "порядок",
            "bucket": "named",
            "verdict": "named_annex",
            "graph": "hold",
            "why": (
                "перечень/порядок — named annex утверждающего указа/распоряжения, "
                "свой DATE+N нет"
            ),
        }
    if not candidates:
        return {
            "lemma": lemma,
            "bucket": "unknown",
            "verdict": "unknown_kind",
            "graph": "refuse",
            "why": "вида нет в словаре — не выдумываем узел графа",
        }
    _exact, _n, family, key = max(candidates, key=lambda row: (row[0], row[1]))
    lemma = key
    if family == "skip":
        return {
            "lemma": lemma,
            "bucket": "skip_as_type",
            "verdict": "not_an_act",
            "graph": "refuse",
            "why": "извещение/лот/заявка — не идентифицирующий акт, в граф НПА не кладём",
        }
    if family == "instrument":
        return {
            "lemma": lemma,
            "bucket": "instrument",
            "verdict": "instrument_not_npa",
            "graph": "refuse",
            "why": "доверенность/жалоба/контракт — документ, но не НПА; ребро «цитирует акт» было бы ложным",
        }
    if family == "named":
        return {
            "lemma": lemma,
            "bucket": "named",
            "verdict": "named_annex",
            "graph": "hold",
            "why": "положение/правила — часто приложение, не отдельный идентифицирующий акт без издателя",
        }
    return {
        "lemma": lemma,
        "bucket": family,
        "verdict": "form_in_dictionary",
        "graph": "undecided",  # ребро решает слой B/F/G, не bucket agency
        "why": f"форма из закрытого списка ({family}); класс ещё не решён",
    }


_AXES: dict[str, object] | None = None


def axes_contract() -> dict[str, object]:
    global _AXES
    if _AXES is None:
        data = yaml.safe_load(AXES_PATH.read_text(encoding="utf-8"))
        if data.get("schema_version") != "law-nexus-npa-classification-axes/v1":
            raise SystemExit(f"unexpected axes schema: {data.get('schema_version')!r}")
        _AXES = data
    return _AXES


_FED_ORG = re.compile(
    r"(?<!\w)(Мин[а-яё]+развития|Мин[а-яё]{3,}|ФАС|УФАС|ФАНО|Росимуществ\w*|"
    r"Правительств\w*\s+РФ|Президент\w*\s+РФ|КС\s+РФ)(?!\w)",
    re.I,
)
_Oblast = r"[А-ЯЁ][а-яё]+(?:ской|цкой|ской)"
_GEO_SUBJ = re.compile(
    r"("
    r"(?:" + _Oblast + r"(?:,\s*" + _Oblast + r")+\s+и\s+" + _Oblast + r"\s+област\w*)|"
    r"(?:" + _Oblast + r"(?:\s+и\s+" + _Oblast + r")?\s+област\w*)|"
    r"(?:город[ае]?\s+[А-ЯЁ][а-яё]+)|"
    r"(?:г\.\s*[А-ЯЁ][а-яё]+)|"
    r"Челябинск\w*|Брянск\w*|Белгород\w*|Магадан\w*|"
    r"Владимирск\w*|Ивановск\w*|Костромск\w*|Ярославск\w*|Смоленск\w*"
    r")",
)
_GEO_CITY_STEM = (
    ("челябинск", "Челябинск"),
    ("брянск", "Брянск"),
    ("белгород", "Белгород"),
    ("магадан", "Магадан"),
)
_TERRITORIAL_FOIV = re.compile(
    r"(УФАС|МТУ\s+Росимущества|управлени\w*\s+федеральн)",
    re.I,
)


def canon_geo(raw: str) -> str:
    """Ось D — топоним, не падеж прилагательного (D382). Competence не трогаем."""
    folded = raw.casefold().strip()
    if not folded:
        return ""
    if "област" in folded or re.search(r"\bгород|\bг\.", folded):
        return re.sub(r"\s+", " ", raw).strip()
    for stem, nom in _GEO_CITY_STEM:
        if folded.startswith(stem):
            return nom
    return re.sub(r"\s+", " ", raw).strip()


def classify_layers(
    canon: str | None, text: str, form: dict[str, str]
) -> dict[str, str]:
    """Оси D516 поверх формы. Не второй словарь видов."""
    ax = axes_contract()
    lemma = form.get("lemma") or ""
    bucket = form.get("bucket") or ""
    folded = (canon or "").casefold()
    body = text.casefold()

    legal_class = "unknown"
    competence = "unknown"
    geo = ""
    issuer = ""
    normativity = "unknown"
    binding = "not_applicable"
    admin = "not_administrative"
    graph = "hold"
    why = form.get("why") or ""

    # GEO/ORG только из слота TYPE (канон члена), не из чужого ФЗ в том же w:p.
    org_hit = _FED_ORG.search(canon or "")
    if org_hit:
        issuer = re.sub(r"\s+", " ", org_hit.group(1)).strip()
    tail_org = re.match(
        r"^(?:письмо|приказ|распоряжение|решение)\s+(.+)$",
        canon or "",
        re.I,
    )
    if tail_org:
        issuer = re.sub(r"\s+", " ", tail_org.group(1)).strip()
    geo_hit = _GEO_SUBJ.search(canon or "")
    territorial_type = bool(
        _TERRITORIAL_FOIV.search(canon or "")
        or lemma in {"письмо", "приказ", "распоряжение"}
        or "уфас" in folded
        or "мту" in folded
    )
    if not geo_hit and territorial_type:
        geo_hit = _GEO_SUBJ.search(text or "")
    if geo_hit:
        geo = canon_geo(geo_hit.group(0))

    std_hit = _ISO_STD.search(canon or "")
    if std_hit:
        fam = std_hit.group("fam").casefold()
        if "регламент" in fam or fam.startswith("тр"):
            international = bool(re.search(r"тс|еаэс|таможенн", fam))
            legal_class = "npa"
            competence = "international" if international else "federal"
            normativity = "yes"
            binding = "yes_if_in_force"
            graph = "overlay" if international else "identifying_act"
            why = (
                "технический регламент (ТР ТС/ЕАЭС) — обязательный; "
                "голый «ТР» не ловим (омограф «третье»); "
                "international identity_key deferred-undefined"
            )
            return _layer_row(
                form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
            )
        legal_class = "unknown"
        competence = (
            "international"
            if re.search(r"iso|iec|^изо|исо", fam)
            else "federal"
        )
        graph = "overlay"
        why = (
            "ГОСТ/ИСО/СНиП/СанПиН — стандарт, не НПА ПП 1009; "
            "обязательность только через техрегламент; не Work identity"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )

    # Решение территориального ФАС/УФАС — практика (ADR-0020), не НПА.
    # Формы «решение» нет в frozen identifying-cycle; ось B здесь, не второй словарь TYPE.
    if re.search(r"решени\w*.*\b(?:уфас|фас)\b", folded) or (
        lemma.startswith("решени") and re.search(r"\b(?:уфас|фас)\b", folded)
    ):
        legal_class = "individual_legal_act"
        competence = "federal"
        if geo_hit:
            geo = canon_geo(geo_hit.group(0))
        normativity = "no"
        binding = "no"
        admin = "administrative_individual"
        graph = "overlay"
        why = (
            "решение УФАС/ФАС по делу — индивидуальный акт территориального ФОИВ, "
            "не НПА и не ступенька ADR-0019; overlay практики (ADR-0020); "
            "GEO города не делает его муниципальным"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if form["verdict"] in {"type_missing", "unknown_kind", "not_an_act"}:
        legal_class = "unknown" if form["verdict"] != "not_an_act" else "unknown"
        graph = "refuse"
        why = form["why"]
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if lemma == "письмо" or bucket == "agency" and folded.startswith("письм"):
        legal_class = str(ax["form_is_not_class"]["pismo"])
        competence = "federal"  # ФОИВ / территориальный ФОИВ, даже если GEO=город
        if _TERRITORIAL_FOIV.search(canon or "") or _TERRITORIAL_FOIV.search(text):
            competence = "federal"
        normativity = str(ax["axes"]["normativity"]["letter_form"])
        binding = "no"
        admin = "administrative_clarification"
        graph = "refuse"
        why = (
            "письмо ФОИВ — не НПА (ПП 1009) и не общеобязательно; "
            "GEO города не делает его муниципальным; ребро идентичности НПА не строим"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if form["verdict"] == "instrument_not_npa" or lemma in {
        "доверенность",
        "жалоба",
        "контракт",
        "лицензия",
        "соглашение",
        "протокол",
    }:
        legal_class = "primary_instrument"
        competence = "not_applicable"
        normativity = "no"
        binding = "not_applicable"
        graph = "refuse"
        why = (
            "простой/первичный документ: не акт власти как источник права; "
            "не нормативность, не общеобязательность"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if "пленум" in folded:
        legal_class = "judicial_act"
        competence = "federal"
        normativity = "no"
        binding = "no"
        admin = "not_administrative"
        graph = "overlay"
        plenary = "Пленум ВАС РФ" if "вас" in folded else "Пленум ВС РФ"
        why = (
            f"постановление {plenary} — разъяснение практики, не НПА и не ступенька ADR-0019; "
            "overlay судебной практики (ADR-0020)"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer or plenary,
            normativity, binding, admin, graph, why,
        )
    if "кс рф" in folded or lemma == "постановление" and "кс рф" in body and "кс" in folded:
        ks = ax["ks_rf_exception"]
        legal_class = str(ks["legal_class"])
        competence = "federal"
        normativity = str(ks["normativity"])
        binding = str(ks["general_bindingness"])
        admin = "not_administrative"
        graph = "overlay"
        why = (
            "постановление КС — не НПА и не ступенька ADR-0019, "
            "но общеобязательно в части судьбы проверенной нормы (исключение G без F)"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer or "КС РФ", normativity, binding, admin, graph, why
        )
    if lemma == "тк" or folded == "тк":
        legal_class = "unknown"
        graph = "refuse"
        why = (
            "голый ТК — омограф (трудовой / таможенный / торговый комплекс); "
            "без полного имени, соседа ТС/ЕАЭС или уже выбранного канона в документе "
            "OfficialIdentityClaim не проецируем (D517)"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if lemma == "кодекс" or folded.startswith("коап") or "кодекс" in folded:
        named = None
        if folded.startswith("коап") or "коап" in folded:
            named = "КоАП РФ"
        elif ("процессуальн" in folded and "гражданск" in folded) or folded.startswith("гпк"):
            named = "ГПК РФ"
        elif "уголовно-процессуальн" in folded or folded.startswith("упк"):
            named = "УПК РФ"
        elif folded.startswith("апк") or "арбитражн" in folded:
            named = "АПК РФ"
        elif folded.startswith("кас") or "судопроизводств" in folded:
            named = "КАС РФ"
        elif re.search(r"таможенн\w*\s+кодекс", folded):
            named = "Таможенный кодекс"
        elif re.search(r"трудов\w*\s+кодекс", folded):
            named = "Трудовой кодекс"
        elif re.search(r"уголовно-исполнительн\w*\s+кодекс", folded) or "уик" in folded:
            named = "Уголовно-исполнительный кодекс"
        elif re.search(r"гражданск\w*\s+кодекс", folded):
            named = "Гражданский кодекс"
        elif re.search(r"уголовн\w*\s+кодекс", folded):
            named = "Уголовный кодекс"
        elif folded.startswith("нк") or "налогов" in folded:
            named = "НК РФ"
        elif folded.startswith("бк") or "бюджетн" in folded:
            named = "БК РФ"
        elif folded.startswith("зк") or "земельн" in folded:
            named = "ЗК РФ"
        elif folded.startswith("жк") or "жилищн" in folded:
            named = "ЖК РФ"
        elif folded.startswith("ск") or "семейн" in folded:
            named = "СК РФ"
        elif folded.startswith("лк") or re.search(r"лесн\w*\s+кодекс", folded):
            named = "ЛК РФ"
        if named == "КоАП РФ" or folded.startswith("коап"):
            koap = ax["koap"]["code"]
            legal_class = str(koap["legal_class"])
            competence = str(koap["competence"])
            normativity = "yes"
            binding = "yes_if_in_force"
            admin = str(koap["administrativeness"])
            graph = "identifying_act"
            why = "КоАП как кодекс = ФЗ; постановление по делу КоАП сюда не входит"
            return _layer_row(
                form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
            )
        legal_class = "npa"
        competence = "federal"
        normativity = "yes"
        binding = "yes_if_in_force"
        admin = "not_administrative"
        graph = "identifying_act"
        why = (
            f"полное имя кодекса ({named or canon}) — НПА, не голый ТК; "
            "омограф аббревиатуры здесь не стоит"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if lemma == "распоряжение" and "правительств" not in folded:
        legal_class = "unknown"
        competence = "federal" if org_hit or _TERRITORIAL_FOIV.search(canon or "") else "unknown"
        normativity = "unknown"
        binding = "not_applicable"
        graph = "hold"
        why = (
            "распоряжение органа — форма, не класс: как приказ бывает НПА и индивидуальным; "
            "распоряжение Правительства — отдельная ветка НПА"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if lemma == "приказ" or (bucket == "agency" and folded.startswith("приказ")):
        if not issuer and _CORP_ACTOR.search(text or ""):
            legal_class = "primary_instrument"
            competence = "not_applicable"
            normativity = "no"
            binding = "not_applicable"
            graph = "refuse"
            why = (
                "приказ юрлица (ООО/АО/ИП) — не акт ФОИВ; "
                "не НПА и не hold до F"
            )
            return _layer_row(
                form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
            )
        legal_class = "unknown"  # YAML: prikaz = [npa, individual_legal_act]
        competence = "federal" if org_hit else "unknown"
        if _TERRITORIAL_FOIV.search(canon or "") or _TERRITORIAL_FOIV.search(text):
            competence = "federal"
        if re.search(r"област", (issuer or canon or "").casefold()) or (
            geo and re.search(r"област", geo.casefold()) and "росси" not in (issuer or "").casefold()
        ):
            competence = "subject"
        normativity = "unknown"
        binding = "not_applicable"
        admin = "administrative_npa" if "утвержден" in body else "unknown"
        graph = "hold"
        why = (
            "приказ — форма, не класс: бывает НПА и индивидуальный; "
            "пока F неясна, OfficialIdentityClaim не проецируем"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if bucket in {"federal", "presidential", "government"} or lemma in {
        "закон",
        "указ",
        "постановление",
        "распоряжение",
        "кодекс",
    }:
        legal_class = "npa"
        competence = "federal"
        normativity = "yes"
        binding = "yes_if_in_force"
        admin = "not_administrative"
        if lemma == "постановление" and "кс" not in folded:
            admin = "not_administrative"
        graph = "identifying_act"
        why = (
            "форма закона/указа/постановления Правительства — НПА; "
            "общеобязательность после режима силы (публикация), не из номера"
        )
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    if form["verdict"] == "named_annex":
        legal_class = "unknown"
        graph = "hold"
        why = form["why"]
        return _layer_row(
            form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
        )
    graph = "hold"
    why = "класс по форме не закрыт — ребро идентичности не строим"
    return _layer_row(
        form, legal_class, competence, geo, issuer, normativity, binding, admin, graph, why
    )


def _layer_row(
    form: dict[str, str],
    legal_class: str,
    competence: str,
    geo: str,
    issuer: str,
    normativity: str,
    binding: str,
    admin: str,
    graph: str,
    why: str,
) -> dict[str, str]:
    key = "hold"
    if legal_class == "npa" and competence in {"federal", "subject", "municipal"}:
        if competence == "federal":
            key = "presidential_agency" if form.get("lemma") in {"приказ", "письмо", "указ"} else "federal"
            if form.get("lemma") in {"закон", "кодекс"}:
                key = "federal"
            elif form.get("lemma") in {"указ"}:
                key = "presidential_agency"
            elif form.get("lemma") in {"постановление", "распоряжение"}:
                key = "presidential_agency"
            elif competence == "federal":
                key = "presidential_agency" if form.get("lemma") in {"приказ", "письмо"} else "federal"
        elif competence in {"subject", "municipal"}:
            key = "regional_municipal"
    if legal_class in {"unknown", "clarification_letter", "primary_instrument"}:
        key = "do_not_project"
    if legal_class == "judicial_act":
        key = "overlay_not_rank"
    if competence == "international":
        key = "deferred-undefined"
    return {
        **form,
        "legal_class": legal_class,
        "competence": competence,
        "geo": geo,
        "issuer": issuer,
        "normativity": normativity,
        "binding": binding,
        "admin": admin,
        "graph": graph,
        "why": why,
        "identity_key": key,
    }


@dataclass
class Block:
    fragment_id: str
    doc_id: str
    order: int  # source_block_index
    note_kind: str
    text: str

    @property
    def ends_open(self) -> bool:
        s = self.text.rstrip()
        # Голова «(в ред. … N 426,» или незакрытая скобка этой конструкции.
        if ED_NOTE.match(s) and (s.endswith(",") or s.count("(") > s.count(")")):
            return True
        # «с изм., внесенными Постановлением КС РФ» — TYPE здесь, дата на следующем w:p.
        # Если дата уже в этом абзаце (027: «… N 34-П)») — это не обрыв.
        if IZM_NOTE.match(s) and not OT_DATE.search(s):
            return True
        # Средний хвост списка: «от DATE N …,» — продолжает серию.
        # Не жалоба/«далее — Закон…,» и не «(диплом),».
        if self.starts_ot_tail and s.endswith(","):
            return True
        return False

    @property
    def starts_ot_tail(self) -> bool:
        return bool(re.match(r"^\s*от\s+\d{2}\.\d{2}\.\d{4}", self.text))


@dataclass
class Edge:
    kind: str  # follows | continues_series | document_head
    src: str
    dst: str
    why: str


@dataclass
class Member:
    date: str
    number: str
    type_name: str | None  # именительный ед.ч. (слот)
    type_written: str | None  # как в тексте («Указов»), не трогаем span
    type_from: str  # written_here | inherited_from_series_head | same_act_in_document | scoped_alias | this_document_ref | missing
    block_id: str
    snippet: str
    type_bucket: str = ""
    type_verdict: str = ""
    graph: str = ""
    type_why: str = ""
    legal_class: str = ""
    competence: str = ""
    geo: str = ""
    issuer: str = ""
    normativity: str = ""
    binding: str = ""
    admin: str = ""
    identity_key: str = ""
    pos: int = -1
    alias: str = ""
    consultant_ref: str = ""  # consultantplus://offline/ref=… — provenance, не Work identity
    consultant_tip: str = ""  # screenTip: полное имя акта у Консультанта
    approved_by: str = ""  # цитата утверждающего акта; свой DATE+N у приложения нет


@dataclass
class DocGraph:
    doc_id: str
    source_path: str
    doc_type: str
    blocks: list[Block]
    edges: list[Edge] = field(default_factory=list)

    def by_id(self) -> dict[str, Block]:
        return {b.fragment_id: b for b in self.blocks}

    def head(self) -> Block:
        return min(self.blocks, key=lambda b: b.order)


def load_docs(root: Path, only: str | None) -> list[DocGraph]:
    man = json.loads((root / MANIFEST.relative_to(ROOT) if False else MANIFEST).read_text())
    default = {
        "npa-doc-001",  # кодекс в тексте правки КоАП; «настоящего Кодекса»
        "npa-doc-002",  # правка КоАП; «настоящего Кодекса» ≠ шапка 396-ФЗ (Duma head)
        "npa-doc-003",  # «настоящего Федерального закона»; диапазон статей 16.6-16.6-2
        "npa-doc-004",  # тот же this_ref + статьи 16.6-16.6-2 (вторая редакция XML)
        "npa-doc-005",  # введён ФЗ N 351/337/459; в ред. 232-ФЗ
        "npa-doc-006",  # «введён ФЗ»; два ФЗ в одной скобке (459 + ред. 232)
        "npa-doc-008",  # «частями 2.1 - 2.3 статьи 19»; this_ref ФЗ
        "npa-doc-007",  # 151-ФЗ + «настоящего Федерального закона»; overlay КС 34-П
        "npa-doc-009",  # Пленум ВАС РФ; «настоящего Федерального закона» = 44-ФЗ
        "npa-doc-010",  # тот же Пленум ВАС + this_ref 44-ФЗ
        "npa-doc-011",  # Пленум ВАС + this_ref 44-ФЗ (вторая редакция XML)
        "npa-doc-037",  # «дополнить частями/пунктами» без статьи — диагностика
        "npa-doc-012",  # сирота «от 09.04.2020 N 16-П)» — голова КС не в seed
        "npa-doc-013",  # Приказ Минэкономразвития
        "npa-doc-014",  # Приказ ФАНО; «настоящего Положения»
        "npa-doc-015",  # Приказы Росгидромета, длинная «в ред.»
        "npa-doc-016",  # Приказы Роструда
        "npa-doc-017",  # Приказы Минэка, длинная «в ред.»
        "npa-doc-018",  # Приказ Минобрнауки; Регламент в названии — не TYPE
        "npa-doc-019",
        "npa-doc-020",
        "npa-doc-021",  # две одинаковые серии постановлений
        "npa-doc-022",
        "npa-doc-023",  # распоряжение Правительства 1765-р
        "npa-doc-024",  # повтор «в ред.» одного распоряжения 508-р
        "npa-doc-025",  # распоряжения Правительства, длинная «в ред.»
        "npa-doc-026",
        "npa-doc-027",  # далее — Закон N 44-ФЗ / 2487-1 / Постановление N 957
        "npa-doc-028",  # доверенность; Закона N 44-ФЗ БЕЗ объявления в этом XML
        "npa-doc-029",  # Пленум ВС + инверсия КС «Суд в Постановлении»
        "npa-doc-030",  # Правила, утв. постановлением; приказы Минздрава
        "npa-doc-031",  # доп. соглашение к контракту — не НПА
        "npa-doc-032",  # письмо Челябинского УФАС + жалоба; далее — Положение
        "npa-doc-033",  # ещё письмо УФАС
        "npa-doc-034",  # жалоба б/н без N; inbound; 4 области
        "npa-doc-035",  # далее — Правила + Конкурсная документация
        "npa-doc-036",  # жалоба б/н + письмо Магаданского УФАС
        "npa-doc-038",  # приказы МВД, повтор «в ред.»
        "npa-doc-039",  # КоАП как кодекс; УИК/ГПК в seed
        "npa-doc-040",  # ИСО 9000:2005 — стандарт, не НПА
    }
    wanted = {only} if only else default
    out: list[DocGraph] = []
    docs = {d["doc_id"]: d for d in man["documents"]}
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for frag in man["fragments"]:
        if frag["doc_id"] in wanted:
            by_doc[frag["doc_id"]].append(frag)
    for doc_id, frags in by_doc.items():
        frags.sort(key=lambda f: f["source_block_index"])
        blocks = []
        for f in frags:
            text = (FIX / f["file"]).read_text(encoding="utf-8")
            blocks.append(
                Block(
                    fragment_id=f["id"],
                    doc_id=doc_id,
                    order=f["source_block_index"],
                    note_kind=f["note_kind"],
                    text=text,
                )
            )
        meta = docs[doc_id]
        g = DocGraph(
            doc_id=doc_id,
            source_path=meta["source_path"],
            doc_type=meta["doc_type"],
            blocks=blocks,
        )
        g.edges = build_edges(g)
        out.append(g)
    out.sort(key=lambda g: g.doc_id)
    return out


def build_edges(g: DocGraph) -> list[Edge]:
    edges: list[Edge] = []
    ordered = sorted(g.blocks, key=lambda b: b.order)
    head = ordered[0]
    for b in ordered[1:]:
        if b.order == 0:
            continue
        edges.append(
            Edge(
                "document_head",
                b.fragment_id,
                head.fragment_id,
                "шапка этого же XML (тип/номер текущего акта, не чужого)",
            )
        )
    for a, b in zip(ordered, ordered[1:]):
        gap = b.order - a.order
        edges.append(
            Edge(
                "follows",
                a.fragment_id,
                b.fragment_id,
                f"следующий сохранённый блок, разрыв индексов={gap}",
            )
        )
        if gap <= 2 and a.ends_open and b.starts_ot_tail:
            edges.append(
                Edge(
                    "continues_series",
                    a.fragment_id,
                    b.fragment_id,
                    "голова списка оборвалась, хвост начинается с «от ДАТА N»",
                )
            )
    return edges


def series_chains(g: DocGraph) -> list[list[str]]:
    nxt = {e.src: e.dst for e in g.edges if e.kind == "continues_series"}
    starts = [b.fragment_id for b in g.blocks if b.fragment_id in nxt]
    seen: set[str] = set()
    chains: list[list[str]] = []
    for start in starts:
        if start in seen:
            continue
        # start of chain = node that nobody continues into
        inbound = {e.dst for e in g.edges if e.kind == "continues_series"}
        if start in inbound:
            continue
        chain = [start]
        seen.add(start)
        cur = start
        while cur in nxt:
            cur = nxt[cur]
            chain.append(cur)
            seen.add(cur)
        if len(chain) >= 2:
            chains.append(chain)
    return chains


def _types_in_text(text: str) -> list[tuple[int, str, str]]:
    found: list[tuple[int, str, str]] = []
    std_spans: list[tuple[int, int]] = []
    dalee_spans = [(m.start(), m.end()) for m in DALEE.finditer(text)]
    this_spans = [(m.start(), m.end()) for m in THIS_REF.finditer(text)]
    for m in _ISO_STD.finditer(text):
        written = re.sub(r"\s+", " ", m.group(0)).strip()
        found.append((m.start(), written, canon_act_type(written)))
        std_spans.append((m.start(), m.end()))
    for m in TYPE_HEAD.finditer(text):
        if any(s <= m.start() < e for s, e in std_spans):
            continue
        if any(s <= m.start() < e for s, e in dalee_spans):
            continue
        if any(s <= m.start() < e for s, e in this_spans):
            continue  # «настоящего ФЗ/Кодекса» — не безымянный член
        written = re.sub(r"\s+", " ", m.group(1)).strip()
        written = re.sub(r"\s+от$", "", written, flags=re.I)
        written = re.sub(r"\.+$", "", written)
        written = re.sub(r"\s+N$", "", written, flags=re.I)
        found.append((m.start(), written, canon_act_type(written)))
    return found


def _type_for_span(
    types: list[tuple[int, str, str]],
    pos: int,
    inherited: str | None,
    date_starts: list[int] | None = None,
) -> tuple[str | None, str, str | None]:
    before = [row for row in types if row[0] <= pos]
    if date_starts:
        filtered = [
            row
            for row in before
            if not any(row[0] < d < pos for d in date_starts)
        ]
        if filtered:
            before = filtered
    if not before:
        return (inherited, "inherited_from_series_head", None) if inherited else (None, "missing", None)
    _start, written, canon = max(before, key=lambda row: row[0])
    return canon, "written_here", written


def parse_members(
    text: str, block_id: str, inherited_type: str | None
) -> tuple[list[Member], str | None]:
    types = _types_in_text(text)
    inbound = {m.start() for m in INBOUND.finditer(text)}
    local_canon = types[0][2] if types else None
    local_written = types[0][1] if types else None
    members: list[Member] = []
    date_hits = [
        dm
        for dm in OT_DATE.finditer(text)
        if not any(s <= dm.start() < s + 80 for s in inbound)
    ]
    minjust_spans = [(h.start(), h.end()) for h in _MINJUST.finditer(text)]
    duma_hits = [
        dm
        for dm in OT_DUMA.finditer(text)
        if not any(s <= dm.start() < s + 80 for s in inbound)
        and not any(abs(dm.start() - ot.start()) < 8 for ot in date_hits)
        and not any(s <= dm.start() < e for s, e in minjust_spans)
    ]
    date_starts = [dm.start() for dm in date_hits] + [dm.start() for dm in duma_hits]
    used_types: set[int] = set()
    seen_canons: set[str] = set()
    ctx_carry = CTX_CARRY.search(text)
    for dm in date_hits:
        date, number = dm.group(1), dm.group(2) or dm.group(3)
        t, src, tw = _type_for_span(types, dm.start(), inherited_type, date_starts)
        if (
            t is None
            and ctx_carry
            and dm.start() <= ctx_carry.start(3)
            and ctx_carry.end(3) <= dm.end()
            and ctx_carry.group(4) == number
        ):
            t = _ctx_carry_type(ctx_carry.group(1), ctx_carry.group(2))
            src, tw = ("written_here", "Постановления") if t else (None, None)
        for start, _written, canon in types:
            if canon == t and start <= dm.start():
                used_types.add(start)
                break
        snippet = text[max(0, dm.start() - 12) : dm.end() + 2]
        form = classify_type(t, lexicon())
        cls = classify_layers(t, text, form)
        members.append(_member_from_cls(date, number, t, tw, src, block_id, snippet, cls, pos=dm.start()))
        if (
            t in {"Постановление КС РФ", "Постановление Пленума ВС РФ", "Определение ВС РФ"}
            and ctx_carry
            and dm.start() <= ctx_carry.start(3)
            and ctx_carry.end(3) <= dm.end()
            and not any(row[0] <= dm.start() and row[2] == t for row in types)
        ):
            members[-1].type_why = (
                "«Постановления от DATE N» с вынесенным эмитентом "
                "(правовой позиции … изложенной в …); тип перенесён из оборота этого абзаца"
            )
        if t:
            seen_canons.add(t.casefold())
    for dm in duma_hits:
        month = dm.group(2).casefold()
        mm = _MONTHS_RU.get(month)
        if not mm:
            continue
        date = f"{int(dm.group(1)):02d}.{mm}.{dm.group(3)}"
        number = dm.group(4)
        t, src, tw = _type_for_span(types, dm.start(), inherited_type, date_starts)
        for start, _written, canon in types:
            if canon == t and start <= dm.start():
                used_types.add(start)
                break
        snippet = text[max(0, dm.start() - 12) : dm.end() + 2]
        form = classify_type(t, lexicon())
        cls = classify_layers(t, text, form)
        members.append(
            _member_from_cls(date, number, t, tw, src, block_id, snippet, cls, pos=dm.start())
        )
        if t:
            seen_canons.add(t.casefold())
    # Именованный кодекс без даты/номера (ГК/УИК) — даже если в абзаце уже есть другие акты.
    for start, written, canon in types:
        if start in used_types:
            continue
        folded = canon.casefold()
        annex = (
            folded.startswith("положен")
            or folded.startswith("правил")
            or folded.startswith("переч")
            or folded.startswith("поряд")
            or "документац" in folded
            or "рекомендац" in folded
            or "требован" in folded
            or folded.startswith("регламент")
        )
        annex_key = re.sub(r"\s+", " ", written).casefold()[:48] if annex else folded
        if annex_key in seen_canons:
            continue
        std_canon = bool(_ISO_STD.search(canon) or _ISO_STD.search(written))
        if (
            "кодекс" not in folded
            and folded not in _CODE_ABBREV_CANONS
            and not any(folded.startswith(stem) for stem in _CODE_ABBREV_STEMS)
            and not annex
            and not std_canon
        ):
            continue
        form = classify_type(canon, lexicon())
        cls = classify_layers(canon, text, form)
        members.append(
            _member_from_cls(
                "—",
                "—",
                canon,
                written,
                "written_here",
                block_id,
                text[start : start + 40],
                cls,
                pos=start,
            )
        )
        seen_canons.add(annex_key)
    _link_approved_by(text, members)
    # Нарицательные «положением/правилами…» без утверждающего акта — не named-annex:
    # безцитатный annex минтим только с Заглавной (именованный акт в формальной прозе).
    members = [
        m
        for m in members
        if not (
            m.number in {"", "—"}
            and not m.approved_by
            and (m.type_name or "") in
            {"правила", "положение", "перечень", "порядок", "требования",
             "методические рекомендации", "регламент", "конкурсная документация"}
            and m.type_written
            and m.type_written[:1].islower()
        )
    ]
    # Один акт = один член на абзац: реквизиты в правках повторяются
    # («слова "…" заменить словами "…"»); предпочитаем типизированный член.
    dedup: dict[tuple[str, str], int] = {}
    deduped: list[Member] = []
    for m in members:
        if m.number in {"", "—"}:
            deduped.append(m)  # именованные приложения не дедупим — ключ у всех ('—','—')
            continue
        key = (m.date, m.number)
        j = dedup.get(key)
        if j is None:
            dedup[key] = len(deduped)
            deduped.append(m)
            continue
        cur = deduped[j]
        if not cur.type_name and m.type_name:
            deduped[j] = m
        elif cur.type_name and m.type_name and cur.type_name != m.type_name:
            continue
    members = deduped
    if not members and local_canon:
        form = classify_type(local_canon, lexicon())
        cls = classify_layers(local_canon, text, form)
        members.append(
            _member_from_cls(
                "—",
                "—",
                local_canon,
                local_written,
                "written_here",
                block_id,
                text[:80],
                cls,
                pos=0,
            )
        )
    return members, local_canon


_APPROVE_VERB = re.compile(r"утвержденн\w*|об\s+утвержден|вместе\s+с", re.I)
_CEO_APPROVE = re.compile(
    r"утвержденн\w*\s+генеральным\s+директором.{0,80}?(\d{2}\.\d{2}\.\d{4})",
    re.I | re.S,
)


def _link_approved_by(text: str, members: list[Member]) -> None:
    """Правила/положение, утв. актом: цитата обязательна, DATE+N приложения не крадём."""
    annexes = [
        m
        for m in members
        if m.number in {"", "—"}
        and (m.type_name or "").casefold()
        in {"правила", "положение", "конкурсная документация", "перечень", "порядок",
            "методические рекомендации", "регламент", "требования"}
    ]
    dated = [m for m in members if m.number not in {"", "—"}]
    vmeste = next((h.start() for h in re.finditer(r"вместе\s+с", text, re.I)), None)
    for annex in annexes:
        later = [m for m in dated if 0 < m.pos - annex.pos < 450]
        earlier = [m for m in dated if 0 < annex.pos - m.pos < 700]
        approver = None
        if later:
            cand = min(later, key=lambda m: m.pos)
            mid = text[annex.pos : cand.pos]
            if _APPROVE_VERB.search(mid):
                approver = cand
        if approver is None and earlier:
            cand = max(earlier, key=lambda m: m.pos)
            mid = text[cand.pos : annex.pos + 80]
            if _APPROVE_VERB.search(mid):
                approver = cand
        # «(вместе с "Правилами…", "Правилами…", "Дополнительными требованиями…")»
        # — все приложения одного акта; окно 450 режет хвост списка.
        if (
            approver is None
            and vmeste is not None
            and annex.pos > vmeste
        ):
            before = [m for m in dated if m.pos < vmeste]
            if before:
                approver = max(before, key=lambda m: m.pos)
        if (annex.type_name or "").casefold() == "регламент":
            window = text[annex.pos : annex.pos + 280]
            hit = _CEO_APPROVE.search(window)
            ceo_bare = re.search(r"генеральным\s+директором", window, re.I)
            if hit or ceo_bare:
                annex.approved_by = (
                    f"генеральный директор от {hit.group(1)}"
                    if hit
                    else "генеральный директор (дата обрезана в seed)"
                )
                annex.graph = "refuse"
                annex.legal_class = "primary_instrument"
                annex.competence = "not_applicable"
                annex.normativity = "no"
                annex.identity_key = "do_not_project"
                annex.type_why = (
                    f"корпоративный регламент площадки, утв. {annex.approved_by}; "
                    "гендиректор АО ≠ ФОИВ, dest не выдумываем"
                )
                continue
            if _CORP_ACTOR.search(window):
                annex.graph = "refuse"
                annex.legal_class = "primary_instrument"
                annex.competence = "not_applicable"
                annex.normativity = "no"
                annex.identity_key = "do_not_project"
                annex.approved_by = annex.approved_by or "АО (корпоративный, не ФОИВ)"
                annex.type_why = (
                    "регламент электронной площадки АО — не акт ФОИВ; "
                    "утверждающий орган в seed не разобран, dest не выдумываем"
                )
                continue
        if approver is None:
            continue
        cite = f"{approver.type_name} от {approver.date} N {approver.number}"
        annex.approved_by = cite
        gov = bool(
            re.search(
                r"правительств|указ\s+президента",
                (approver.type_name or "").casefold(),
            )
        )
        if gov and (annex.type_name or "").casefold() in {
            "правила", "положение", "перечень", "порядок", "требования"
        }:
            annex.legal_class = "npa"
            annex.competence = "federal"
            annex.normativity = "yes"
            annex.binding = "yes_if_in_force"
            annex.graph = "identifying_act"
            annex.identity_key = "federal"
            annex.type_why = (
                f"правила/положение, утв. {cite} — нормативный акт; "
                "свой DATE+N нет, цитата через утверждающий акт; Work не склеиваем"
            )
        else:
            annex.type_why = (
                f"named annex, утв. {cite}; "
                "свой DATE+N нет, цитата через утверждающий акт; Work не склеиваем"
            )


def _member_from_cls(
    date: str,
    number: str,
    t: str | None,
    tw: str | None,
    src: str,
    block_id: str,
    snippet: str,
    cls: dict[str, str],
    pos: int = -1,
    alias: str = "",
) -> Member:
    return Member(
        date,
        number,
        t,
        tw,
        src,
        block_id,
        snippet.replace("\n", " "),
        type_bucket=cls["bucket"],
        type_verdict=cls["verdict"],
        graph=cls["graph"],
        type_why=cls["why"],
        legal_class=cls["legal_class"],
        competence=cls["competence"],
        geo=cls["geo"],
        issuer=cls["issuer"],
        normativity=cls["normativity"],
        binding=cls["binding"],
        admin=cls["admin"],
        identity_key=cls["identity_key"],
        pos=pos,
        alias=alias,
    )


_HLINK_RE = re.compile(r"<w:hlink([^>]*)>(.*?)</w:hlink>", re.S)
_XML_HLINKS: dict[str, list[tuple[str, str, str]]] = {}


def _decode_consultant_text(s: str) -> str:
    """screenTip / w:t: &#34; &#60; &#62; и перевод строки. Не парсим продукт."""
    s = html.unescape(s or "")
    s = s.replace("{КонсультантПлюс}", "").replace("\n", " ")
    return re.sub(r"\s+", " ", s).strip()


def _xml_hlinks(source_path: str) -> list[tuple[str, str, str]]:
    """(visible, dest, screenTip) из w:hlink. Кэш по XML. Не парсим продукт."""
    key = str(source_path)
    if key in _XML_HLINKS:
        return _XML_HLINKS[key]
    path = Path(source_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        _XML_HLINKS[key] = []
        return []
    raw = path.read_text(encoding="utf-8", errors="replace")
    out: list[tuple[str, str, str]] = []
    for m in _HLINK_RE.finditer(raw):
        attrs, inner = m.group(1), m.group(2)
        dest_m = re.search(r'w:dest="([^"]*)"', attrs)
        tip_m = re.search(r'w:screenTip="([^"]*)"', attrs)
        dest = dest_m.group(1) if dest_m else ""
        tip = tip_m.group(1) if tip_m else ""
        tip = _decode_consultant_text(tip)
        vis = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", inner))
        vis = _decode_consultant_text(vis)
        if vis or dest:
            out.append((vis, dest, tip))
    _XML_HLINKS[key] = out
    return out


_TIP_PRIMARY = re.compile(
    r"от\s+(\d{2}\.\d{2}\.\d{4})\s+N\s+([0-9А-ЯA-Z]+(?:[/-][0-9А-ЯA-Z]+)*)",
    re.I,
)


def _hlink_indexes(
    source_path: str,
) -> tuple[dict[tuple[str, str], tuple[str, str]], dict[str, tuple[str, str]]]:
    """Первичный идентификатор hlink = первый «от DATE N NUM» в screenTip.
    Видимый «N xxx» — второй ключ. Не берём чужие номера из «о внесении изменений в … N 55».
    """
    by_dn: dict[tuple[str, str], tuple[str, str]] = {}
    by_num: dict[str, tuple[str, str]] = {}
    ambiguous: set[str] = set()
    for vis, dest, tip in _xml_hlinks(source_path):
        # offline/ref = dest акта. internal:// = якорь абзаца/статьи, не dest.
        if dest.startswith("consultantplus-internal://"):
            continue
        if not dest.startswith("consultantplus://"):
            continue
        prim = _TIP_PRIMARY.search(tip)
        vis_num = ""
        if re.match(r"^N\s+", vis, re.I):
            vis_num = vis.split(None, 1)[-1].strip()
        if prim:
            date, num = prim.group(1), prim.group(2)
            by_dn.setdefault((date, num.casefold()), (dest, tip))
            key = num.casefold()
            if key in by_num and by_num[key][0] != dest:
                ambiguous.add(key)
            else:
                by_num.setdefault(key, (dest, tip))
        elif vis_num:
            key = vis_num.casefold()
            by_num.setdefault(key, (dest, tip))
    for key in ambiguous:
        by_num.pop(key, None)  # омограф номера — только (date, N)
    return by_dn, by_num


_TIP_TYPE = re.compile(r"^(.+?)\s+от\s+\d{2}\.\d{2}\.\d{4}", re.I)


def _type_from_tip(tip: str) -> str | None:
    folded = (tip or "").strip().lstrip('"«»')
    hit = _TIP_TYPE.match(folded)
    if not hit:
        return None
    written = hit.group(1).strip().strip('"«»')
    if not written:
        return None
    return canon_act_type(written)


def attach_consultant(g: DocGraph, members: list[Member]) -> list[Member]:
    """Если w:hlink есть — используем dest + screenTip. Нет — не выдумываем. Не Work identity."""
    by_dn, by_num = _hlink_indexes(g.source_path)
    if not by_dn and not by_num:
        return members
    for m in members:
        if not m.number or m.number in {"", "—"}:
            continue
        hit = None
        if m.date not in {"", "—"}:
            hit = by_dn.get((m.date, m.number.casefold()))
        if hit is None:
            hit = by_num.get(m.number.casefold())
            if hit and m.date not in {"", "—"}:
                prim = _TIP_PRIMARY.search(hit[1])
                if prim and prim.group(1) != m.date:
                    hit = None  # омограф номера, другая дата в screenTip
        if not hit:
            continue
        dest, tip = hit
        m.consultant_ref = dest
        m.consultant_tip = tip
        tip_type = _type_from_tip(tip)
        if tip_type:
            form = classify_type(tip_type, lexicon())
            cls = classify_layers(tip_type, tip, form)
            m.type_name = tip_type
            m.legal_class = cls["legal_class"]
            m.graph = cls["graph"]
            m.competence = cls["competence"]
            m.issuer = cls["issuer"] or m.issuer
            m.normativity = cls["normativity"]
            m.binding = cls["binding"]
            m.admin = cls["admin"]
            m.identity_key = cls["identity_key"]
            m.type_why = (
                f"screenTip Consultant: {tip_type}; dest сохранён; не OfficialIdentityClaim"
            )
    return members


def attach_seed_hlink_members(g: DocGraph, members: list[Member]) -> list[Member]:
    """hlink на абзаце seed: dest=offline и tip называет кодекс, которого нет в членах.
    Не весь XML. Не internal://. Не OfficialIdentityClaim.
    """
    bodies = _xml_para_bodies(g.source_path)
    if not bodies:
        return members
    have = {(m.date, m.number.casefold()) for m in members if m.number not in {"", "—"}}
    extra: list[Member] = []
    for b in g.blocks:
        idx = _xml_para_index(g, b)
        if idx is None:
            continue
        _text, raw = bodies[idx]
        for hm in _HLINK_RE.finditer(raw):
            attrs, inner = hm.group(1), hm.group(2)
            dest_m = re.search(r'w:dest="([^"]*)"', attrs)
            tip_m = re.search(r'w:screenTip="([^"]*)"', attrs)
            dest = dest_m.group(1) if dest_m else ""
            if dest.startswith("consultantplus-internal://"):
                continue
            if not dest.startswith("consultantplus://"):
                continue
            tip = _decode_consultant_text(tip_m.group(1) if tip_m else "")
            prim = _TIP_PRIMARY.search(tip)
            if not prim:
                continue
            date, number = prim.group(1), prim.group(2)
            key = (date, number.casefold())
            if key in have:
                continue
            tip_type = _type_from_tip(tip)
            if not tip_type:
                continue
            folded = tip_type.casefold()
            if "кодекс" not in folded and "коап" not in folded:
                continue
            form = classify_type(tip_type, lexicon())
            cls = classify_layers(tip_type, tip, form)
            vis = _decode_consultant_text(
                "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", inner))
            )
            minted = _member_from_cls(
                date,
                number,
                tip_type,
                vis or tip_type,
                "xml_hlink_on_block",
                b.fragment_id,
                vis or tip[:40],
                cls,
                pos=hm.start(),
            )
            minted.type_from = "xml_hlink_on_block"
            minted.consultant_ref = dest
            minted.consultant_tip = tip
            minted.type_why = (
                f"hlink на этом w:p seed: dest + screenTip {tip_type}; "
                "не весь XML, не OfficialIdentityClaim"
            )
            extra.append(minted)
            have.add(key)
    return members + extra


def flow_lonely(block: Block) -> dict:
    """Как сейчас: один абзац, соседа нет."""
    members, local_type = parse_members(block.text, block.fragment_id, None)
    return {
        "mode": "один абзац (как сейчас capture_lawrefs(текст блока))",
        "block": block.fragment_id,
        "text": block.text,
        "open": block.ends_open,
        "tail": block.starts_ot_tail,
        "type_in_this_block": local_type,
        "members": members,
        "problem": _lonely_problem(block, members, local_type),
    }


def _lonely_problem(block: Block, members: list[Member], local_type: str | None) -> str:
    if block.ends_open and local_type:
        return "голова списка: тип есть, скобка не закрыта, остальные номера в другом абзаце — их здесь нет"
    if block.starts_ot_tail and not local_type:
        return "хвост списка: даты и номера есть, ТИПА АКТА нет — система видит «от 14.04.2017 N 446» как будто это отдельный неизвестный документ"
    if members and local_type and not block.ends_open:
        return "этот абзац сам по себе полный — соседа не нужно"
    if not members:
        return "в этом абзаце нет пары дата+номер — одиночный захват ничего не найдёт (или найдёт не то)"
    return "неясно без соседа"


def flow_with_neighbor(g: DocGraph, block: Block) -> dict:
    """Как надо: спросить соседа по рёбрам графа, якоря не склеивать."""
    ids = g.by_id()
    chain = None
    for ch in series_chains(g):
        if block.fragment_id in ch:
            chain = ch
            break
    if not chain:
        lonely = flow_lonely(block)
        lonely["mode"] = "спросить соседа — ребра continues_series нет, остаёмся в одном абзаце"
        lonely["inherited_type"] = None
        lonely["chain"] = [block.fragment_id]
        return lonely

    head_block = ids[chain[0]]
    _, head_type = parse_members(head_block.text, head_block.fragment_id, None)
    all_members: list[Member] = []
    for fid in chain:
        b = ids[fid]
        # тип пишем только с головы; хвосты наследуют
        inherited = None if fid == chain[0] else head_type
        ms, _ = parse_members(b.text, fid, inherited)
        all_members.extend(ms)
    display = "".join(ids[fid].text for fid in chain)
    return {
        "mode": "спросить соседа (ребро continues_series + наследование типа)",
        "block": block.fragment_id,
        "chain": chain,
        "display_join": display,
        "anchors_stay_separate": True,
        "inherited_type": head_type,
        "members": all_members,
        "problem": None
        if head_type and all_members
        else "голову серии нашли, но тип так и не прочитался",
    }


def print_graph(g: DocGraph) -> None:
    print()
    print("=" * 72)
    print(f"ДОКУМЕНТ {g.doc_id}  тип={g.doc_type}")
    print(f"файл XML: …/{Path(g.source_path).name}")
    print("узлы (абзацы, которые попали в seed — не все абзацы XML):")
    for b in sorted(g.blocks, key=lambda x: x.order):
        flag = ""
        if b.ends_open:
            flag += " [оборван]"
        if b.starts_ot_tail:
            flag += " [хвост «от ДАТА»]"
        print(f"  {b.fragment_id:14}  абзац#{b.order:<3} {flag}")
        print(f"       «{b.text[:88]}»")
    print("рёбра:")
    for e in g.edges:
        if e.kind == "document_head":
            continue
        print(f"  {e.src} --{e.kind}--> {e.dst}")
        print(f"       почему: {e.why}")
    chains = series_chains(g)
    if chains:
        print("серии редакции (это и есть «список в ред.», разрезанный Консультантом):")
        for ch in chains:
            print("  " + " → ".join(ch))
    else:
        print("серий редакции в этом куске seed нет")


def print_member_table(members: list[Member], title: str) -> None:
    print(f"  {title}")
    if not members:
        print("    (пусто)")
        return
    print(
        f"    {'дата':<12} {'номер':<14} {'слот TYPE':<28} "
        f"{'класс B':<22} {'F':<8} {'G':<18} {'в граф?':<16}"
    )
    for m in members:
        print(
            f"    {m.date:<12} {m.number:<14} {(m.type_name or 'НЕИЗВЕСТЕН'):<28} "
            f"{m.legal_class:<22} {m.normativity:<8} {m.binding:<18} {m.graph:<16}"
        )
        extra = []
        if m.competence:
            extra.append(f"C={m.competence}")
        if m.geo:
            extra.append(f"GEO={m.geo}")
        if m.issuer:
            extra.append(f"E={m.issuer}")
        if m.admin:
            extra.append(f"H={m.admin}")
        extra.append(f"ключ={m.identity_key}")
        extra.append(m.block_id)
        if m.type_from not in {"written_here", ""}:
            extra.append(f"from={m.type_from}")
        if m.alias:
            extra.append(f"alias={m.alias!r}")
        if m.approved_by:
            extra.append(f"утв. {m.approved_by}")
        print("      " + "  ".join(extra))
        if m.consultant_ref:
            print(f"      consultant {m.consultant_ref[:88]}")
            if m.consultant_tip:
                print(f"      tip: {m.consultant_tip[:140]}")
        if m.graph in {"refuse", "hold", "overlay"} or m.type_from in {
            "scoped_alias",
            "this_document_ref",
        }:
            print(f"      почему: {m.type_why}")


def walk_example(g: DocGraph, fragment_id: str) -> None:
    b = g.by_id()[fragment_id]
    print()
    print("-" * 72)
    print(f"ШАГИ НА ПРИМЕРЕ {fragment_id}")
    print(f"Текст абзаца: «{b.text}»")
    print()
    print("Шаг 1. Лексер видит только ЭТУ строку. Соседа он не знает.")
    lonely = flow_lonely(b)
    print(f"  открытый список? {lonely['open']}   хвост без головы? {lonely['tail']}")
    print(f"  тип, написанный ЗДЕСЬ: {lonely['type_in_this_block']!r}")
    print_member_table(lonely["members"], "что нашли в одном абзаце:")
    print(f"  вывод: {lonely['problem']}")
    print()
    print("Шаг 2. Не склеиваем файлы. Спрашиваем граф: есть ли ребро «продолжение серии»?")
    with_n = flow_with_neighbor(g, b)
    print(f"  цепочка: {' → '.join(with_n['chain'])}")
    if with_n.get("display_join") and with_n["chain"] != [fragment_id]:
        print("  для глаз можно показать склейку (это НЕ новый якорь):")
        print(f"    «{with_n['display_join']}»")
        print(f"  тип, взятый с ГОЛОВЫ серии: {with_n.get('inherited_type')!r}")
        print_member_table(with_n["members"], "что нашли, когда спросили соседа:")
        print("  у каждого номера свой абзац-якорь. Байты 087 не вписали в 086.")
    else:
        print("  соседа по серии нет — остаёмся при шаге 1.")
    print()
    print("Шаг 3. Что из этого следует для человека / Pullenti / нашего кода:")
    if with_n["chain"] != [fragment_id]:
        print("  • человеку показывать цепочку, а не один обрубок")
        print("  • capture должен уметь спросить голову серии, а не только &str блока")
        print("  • Pullenti на ЦЕЛОМ тексте документа как раз так и делает (Sofa)")
        print("  • мы это копировать кодом не будем — копируем правило: тип живёт на голове")
    else:
        print("  • этот абзац самодостаточен, соседа не надо")


def print_layer_matrix() -> None:
    print()
    print("=" * 72)
    print("ОСИ D516 (sidecar YAML, не второй словарь TYPE)")
    ax = axes_contract()
    print(f"  schema={ax['schema_version']}  decision={ax['owner_decision']}")
    print(f"  форма (A) берётся из {ax['form_lexicon']}  (M205 frozen)")
    print(f"  порядок: {' → '.join(ax['order'])}")
    print()
    print(f"  {'ось':<6} {'имя':<22} {'вопрос'}")
    print("  " + "-" * 68)
    for name, spec in ax["axes"].items():
        q = spec.get("question") or spec.get("home") or ""
        print(f"  {spec['id']:<6} {name:<22} {q}")
    print()
    print("  письмо ФОИВ: B=clarification_letter  F=no  G=no  → не в граф НПА")
    print("  приказ:      B=unknown (НПА или индивидуальный) → hold")
    print("  постановление КС: B=judicial_act  F=no  G=yes_as_to_reviewed_norm → overlay")
    print("  КоАП как кодекс:  B=npa  F=yes  H=legislative_on_admin_subject")
    print("  доверенность/жалоба: B=primary_instrument → refuse")
    print("  УФАС в Челябинске: C=federal, GEO=город — не муниципальный акт")


def print_idea_matrix() -> None:
    print()
    print("=" * 72)
    print("МАТРИЦА ИДЕЙ → ЧТО В ГРАФЕ")
    rows = [
        (
            "Pullenti Sofa",
            "весь документ — одна цепочка токенов",
            "узлы-абзацы + ребро follows; анализатор идёт по документу, не по файлу .txt",
        ),
        (
            "Pullenti список указов",
            "TYP, дата, N, дата, N — потом нарезать на акты",
            "ребро continues_series; тип хранится на голове, хвосты наследуют поле, не span",
        ),
        (
            "eyecite resolve",
            "сначала вытащить кусок, потом привязать к стеку документа",
            "шаг 1 = члены в абзаце; шаг 2 = спросить document_head / голову серии",
        ),
        (
            "наша D385",
            "соседа спросить можно, один якорь на два абзаца — нельзя",
            "display_join для глаз; anchors_stay_separate=True",
        ),
        (
            "наша специфика Консультант",
            "длинная «(в ред. …)» рвётся по w:p",
            "детектор: оборван + следующий начинается с «от ДАТА»",
        ),
        (
            "fail-closed",
            "нет головы — не выдумывать «ФЗ»",
            "type_from=missing, не подставлять шапку документа в чужой список редакции",
        ),
        (
            "человек (M207)",
            "кодировать целую отсылку",
            "пакет кодировщика = цепочка, не один npa-frag-087",
        ),
        (
            "C4 / capture сейчас",
            "lex(абзац); capture_lawrefs(абзац)",
            "это только шаг 1. Шаг 2 в трубу не включён — отсюда «нет контекста»",
        ),
    ]
    print(f"{'идея':<24} {'смысл':<44} {'в этом прототипе'}")
    print("-" * 72)
    for idea, sense, here in rows:
        print(f"{idea:<24} {sense:<44}")
        print(f"{'':24} → {here}")


def print_dataflow() -> None:
    print()
    print("=" * 72)
    print("ПОТОК ДАННЫХ ПО ШАГАМ (что получится)")
    steps = [
        "XML Консультанта (весь указ / постановление)",
        "декодер режет на абзацы w:p  →  узлы графа (байты каждого абзаца свои)",
        "индекс документа: follows, document_head, continues_series",
        "ветка А (сейчас): capture(абзац) → «нашли дату+номер» или «ничего»  → ложь на хвосте",
        "ветка Б (надо): capture(абзац) + спросить граф → члены с типом с головы",
        "человеку / диагностике Pullenti показывать ветку Б",
        "слоты «как написано» остаются на своём абзаце; тип на хвосте — ОТДЕЛЬНОЕ поле «унаследован»",
        "resolve / идентичность / Change (M208) едят уже ЧЛЕНОВ СЕРИИ, не сырой w:p",
    ]
    for i, s in enumerate(steps, 1):
        print(f"  {i}. {s}")
    print()
    print("Итог ветки А на 087: «от 14.04.2017 N 446» без слова «Постановление».")
    print("Итог ветки Б на 087: тот же якорь 087, тип = «Постановлений Правительства РФ» с 086.")
    print("Файлы .txt не переписываются. Колесо не изобретается — подключается шаг 2.")


def _inherited_type_for(g: DocGraph, fragment_id: str) -> str | None:
    """Тип с головы continues_series; иначе None."""
    ids = g.by_id()
    for chain in series_chains(g):
        if fragment_id not in chain:
            continue
        head = ids[chain[0]]
        _, head_type = parse_members(head.text, head.fragment_id, None)
        return None if fragment_id == chain[0] else head_type
    return None


_XML_PARAS: dict[str, list[str]] = {}
_XML_PARA_BODIES: dict[str, list[tuple[str, str]]] = {}


def _xml_paragraphs(source_path: str) -> list[str]:
    """w:t каждого w:p исходного XML. Кэш по пути. Не весь документ в парсер."""
    return [text for text, _body in _xml_para_bodies(source_path)]


def _xml_para_bodies(source_path: str) -> list[tuple[str, str]]:
    """(decoded text, raw w:p) — hlink снимаем только с абзаца seed."""
    key = str(source_path)
    if key in _XML_PARA_BODIES:
        return _XML_PARA_BODIES[key]
    path = Path(source_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        _XML_PARA_BODIES[key] = []
        _XML_PARAS[key] = []
        return []
    raw = path.read_text(encoding="utf-8", errors="replace")
    bodies: list[tuple[str, str]] = []
    for m in re.finditer(r"<w:p[\s>]", raw):
        end = raw.find("</w:p>", m.start())
        if end < 0:
            continue
        body = raw[m.start() : end]
        ts = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", body))
        ts = _decode_consultant_text(ts)
        if ts:
            bodies.append((ts, body))
    _XML_PARA_BODIES[key] = bodies
    _XML_PARAS[key] = [t for t, _ in bodies]
    return bodies


def _xml_para_index(g: DocGraph, block: Block) -> int | None:
    needle = re.sub(r"\s+", " ", block.text).strip()
    if not needle:
        return None
    paras = _xml_paragraphs(g.source_path)
    for i, p in enumerate(paras):
        if p == needle or p.endswith(needle) or needle in p:
            return i
    return None


def _xml_neighbor_head(g: DocGraph, block: Block) -> str | None:
    """D385 adjacent_blocks: 1–2 предыдущих w:p источника. Не шапка XML, не весь документ."""
    idx = _xml_para_index(g, block)
    if idx is None or idx == 0:
        return None
    paras = _xml_paragraphs(g.source_path)
    for back in (1, 2):
        if idx - back < 0:
            break
        prev = paras[idx - back]
        if not (IZM_NOTE.match(prev) or ED_NOTE.match(prev) or _types_in_text(prev)):
            continue
        _ms, local = parse_members(prev, f"xml-adj-{block.fragment_id}", None)
        if local:
            return local
        types = _types_in_text(prev)
        if types:
            return types[0][2]
    return None


def _xml_forward_tails(
    g: DocGraph, last: Block, inherited_type: str | None
) -> list[Member]:
    """Seed обрезан запятой: 1–4 следующих w:p, пока это «от DATE N». Стоп на прозе."""
    if not inherited_type:
        return []
    if not (last.starts_ot_tail and last.ends_open):
        return []
    idx = _xml_para_index(g, last)
    if idx is None:
        return []
    paras = _xml_paragraphs(g.source_path)
    extra: list[Member] = []
    for fwd in range(1, 5):
        if idx + fwd >= len(paras):
            break
        nxt = paras[idx + fwd]
        if not re.match(r"^от\s+\d{2}\.\d{2}\.\d{4}", nxt):
            break
        ms, _ = parse_members(nxt, f"xml-fwd:{last.fragment_id}", inherited_type)
        for m in ms:
            if m.type_from == "inherited_from_series_head":
                m.type_from = "xml_adjacent_tail"
                m.type_why = (
                    "хвост серии в следующем w:p источника; seed обрезан запятой; "
                    "TYPE с головы серии, не шапка XML"
                )
            extra.append(m)
        if nxt.rstrip().endswith(")"):
            break  # закрывающая скобка — конец списка
    return extra


def _same_act_index(g: DocGraph) -> dict[tuple[str, str], str]:
    """Первый (дата, номер) в этом XML, у которого уже есть TYPE — повтор цитаты, не серия."""
    index: dict[tuple[str, str], str] = {}
    for b in sorted(g.blocks, key=lambda x: x.order):
        ms, _ = parse_members(b.text, b.fragment_id, None)
        for m in ms:
            if m.date in {"", "—"} or m.number in {"", "—"} or not m.type_name:
                continue
            index.setdefault((m.date, m.number), m.type_name)
    return index


def _is_party_alias(wording: str) -> bool:
    folded = re.sub(r"\s+", " ", wording).strip().casefold()
    head = folded.split()[0] if folded else ""
    if _PARTY_ALIAS.match(head) or _PARTY_ALIAS.match(folded):
        return True
    if re.search(r"организатор|заявитель|истец|ответчик|оператор|продажа|еис|конкурсный отбор", folded):
        return True
    return False


def _alias_keys(wording: str) -> list[str]:
    """Ключи поиска: полное имя, «закон n 44-фз», голый номер. Не голый «закон» — иначе схлопнет несколько актов."""
    folded = re.sub(r"\s+", " ", wording).strip().casefold()
    folded = folded.replace("№", "n").replace("№", "n")
    keys: list[str] = []
    if folded:
        keys.append(folded)
    num = re.search(r"\bn\s+([0-9а-яa-z]+(?:[/-][0-9а-яa-z]+)*)", folded)
    if num:
        keys.append(num.group(1))
        keys.append(f"n {num.group(1)}")
        stem = re.match(r"(закон\w*|постановлен\w*|приказ\w*|указ\w*)", folded)
        if stem:
            keys.append(f"{stem.group(1).rstrip('ыиауеом')} n {num.group(1)}")
    if re.match(r"^(положен\w*|правил\w*|протокол\w*|регламент\w*|методическ\w*)(?:\s|$)", folded):
        if folded.startswith("положен"):
            keys.append("положение")
        elif folded.startswith("правил"):
            keys.append("правила")
        elif folded.startswith("протокол"):
            keys.append("протокол")
        elif folded in {"регламент", "регламента"}:
            keys.append("регламент")
        elif folded.startswith("методическ"):
            keys.append("методические рекомендации")
    # «Регламент УТП» и «Регламент» — разные ключи; голый «регламент» не схлопывает.
    # unique, keep order
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _nearest_member(members: list[Member], pos: int, wording: str) -> Member | None:
    before = [m for m in members if m.pos >= 0 and m.pos < pos]
    if not before:
        return None
    folded = wording.casefold()
    if re.search(r"положен|правил", folded):
        named = [
            m
            for m in before
            if (m.type_name or "").casefold() in {"положение", "правила"}
            and pos - m.pos < 500
        ]
        if named:
            return named[-1]
        return None  # «далее — Положение» без приложения слева — не клеим к постановлению
    if re.search(r"документац", folded):
        named = [
            m
            for m in before
            if "документац" in (m.type_name or "").casefold()
            and pos - m.pos < 500
        ]
        if named:
            return named[-1]
        return None  # «далее — Конкурсная документация» без своего члена — не клеим к приказу
    if re.search(r"регламент", folded):
        regs = [
            m
            for m in before
            if (m.type_name or "").casefold() == "регламент"
            and pos - m.pos < 500
        ]
        if not regs:
            return None  # Регламент в названии приказа — не TYPE
        if "утп" in folded:
            utp = [
                m
                for m in regs
                if "универсальн" in (m.type_written or "").casefold()
                or "утп" in (m.type_written or "").casefold()
            ]
            if utp:
                return utp[-1]
        return regs[-1]
    if re.search(r"протокол", folded):
        proto = [
            m
            for m in before
            if (m.type_name or "").casefold() == "протокол"
            and pos - m.pos < 500
        ]
        if proto:
            return proto[-1]
        return None  # «далее — Протокол» без своего члена — не клеим к приказу
    if re.search(r"\bn\s+([0-9а-яa-z/-]+)", folded):
        num = re.search(r"\bn\s+([0-9а-яa-z]+(?:[/-][0-9а-яa-z]+)*)", folded)
        if num:
            hit = [m for m in before if m.number.casefold() == num.group(1)]
            if hit:
                return hit[-1]
            return None  # номер в «далее» не совпал — не чужой акт слева
    return max(before, key=lambda m: m.pos)


def collect_aliases(g: DocGraph) -> dict[str, Member]:
    """Таблица «далее — X» на весь XML. Несколько актов сразу. Не CurrentDocumentRequisites."""
    table: dict[str, Member] = {}
    for b in sorted(g.blocks, key=lambda x: x.order):
        ms, _ = parse_members(b.text, b.fragment_id, None)
        for hit in DALEE.finditer(b.text):
            wording = re.sub(r"\s+", " ", hit.group(1)).strip()
            if _is_party_alias(wording):
                continue
            target = _nearest_member(ms, hit.start(), wording)
            if target is None:
                continue
            target.alias = wording
            for key in _alias_keys(wording):
                table.setdefault(key, target)
    return table


def _short_ref_covered(text: str, start: int, members: list[Member]) -> bool:
    before = text[max(0, start - 40) : start]
    if re.search(r"от\s+\d{2}\.\d{2}\.\d{4}\s+$", before):
        return True
    if re.search(r"далее\s*[-\u2014]\s*$", before.casefold()):
        return True  # само объявление, не краткая отсылка
    for m in members:
        if m.pos >= 0 and abs(m.pos - start) < 60 and m.number not in {"", "—"}:
            return True
    return False


def _clone_alias_hit(
    target: Member, block_id: str, snippet: str, pos: int, written: str
) -> Member:
    form = classify_type(target.type_name, lexicon())
    cls = classify_layers(target.type_name, snippet, form)
    cloned = _member_from_cls(
        target.date,
        target.number,
        target.type_name,
        written,
        "scoped_alias",
        block_id,
        snippet,
        cls,
        pos=pos,
        alias=target.alias or written,
    )
    cloned.type_from = "scoped_alias"
    cloned.graph = target.graph
    cloned.legal_class = target.legal_class
    cloned.competence = target.competence
    cloned.geo = target.geo
    cloned.issuer = target.issuer
    cloned.normativity = target.normativity
    cloned.binding = target.binding
    cloned.admin = target.admin
    cloned.identity_key = target.identity_key
    cloned.type_why = (
        f"краткая отсылка «{written}» → объявление «далее — {target.alias or target.type_name}» "
        f"в этом XML (D385 scoped_alias), не CurrentDocumentRequisites"
    )
    cloned.consultant_ref = target.consultant_ref
    cloned.consultant_tip = target.consultant_tip
    cloned.approved_by = target.approved_by
    return cloned


_OT_DUMA_NN = re.compile(
    r"от\s+(\d{1,2})\s+([а-яё]+)\s+(\d{4})\s+г(?:ода|\.)?(?!\s*N)",
    re.I,
)
_LETTERHEAD = (
    (re.compile(r"МИНИСТЕРСТВО\s+ВНУТРЕННИХ\s+ДЕЛ", re.I), "МВД России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ЮСТИЦИИ", re.I), "Минюста России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ТРУДА", re.I), "Минтруда России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ФИНАНСОВ", re.I), "Минфина России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ЗДРАВООХРАНЕНИЯ", re.I), "Минздрава России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ПРОМЫШЛЕННОСТИ\s+И\s+ТОРГОВЛИ", re.I), "Минпромторга России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ЭКОНОМИЧЕСКОГО\s+РАЗВИТИЯ", re.I), "Минэкономразвития России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ПРИРОДНЫХ\s+РЕСУРСОВ", re.I), "Минприроды России"),
    (re.compile(r"МИНИСТЕРСТВО\s+СЕЛЬСКОГО\s+ХОЗЯЙСТВА", re.I), "Минсельхоза России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ТРАНСПОРТА", re.I), "Минтранса России"),
    (re.compile(r"МИНИСТЕРСТВО\s+СТРОИТЕЛЬСТВА", re.I), "Минстроя России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ЦИФРОВОГО\s+РАЗВИТИЯ", re.I), "Минцифры России"),
    (re.compile(r"МИНИСТЕРСТВО\s+СВЯЗИ", re.I), "Минкомсвязи России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ОБРАЗОВАНИЯ", re.I), "Минпросвещения России"),
    (re.compile(r"МИНИСТЕРСТВО\s+НАУКИ", re.I), "Минобрнауки России"),
    (re.compile(r"МИНИСТЕРСТВО\s+СПОРТА", re.I), "Минспорта России"),
    (re.compile(r"МИНИСТЕРСТВО\s+КУЛЬТУРЫ", re.I), "Минкультуры России"),
    (re.compile(r"МИНИСТЕРСТВО\s+ЭНЕРГЕТИКИ", re.I), "Минэнерго России"),
    (re.compile(r"ФЕДЕРАЛЬНАЯ\s+АНТИМОНОПОЛЬНАЯ", re.I), "ФАС России"),
    (re.compile(r"ФЕДЕРАЛЬНАЯ\s+СЛУЖБА\s+БЕЗОПАСНОСТИ", re.I), "ФСБ России"),
    (re.compile(r"ФЕДЕРАЛЬНАЯ\s+СЛУЖБА\s+ОХРАНЫ", re.I), "Росгвардия России"),
    (re.compile(r"ФЕДЕРАЛЬНАЯ\s+ТАМОЖЕННАЯ", re.I), "ФТС России"),
    (re.compile(r"ФЕДЕРАЛЬНОЕ\s+КАЗНАЧЕЙСТВО", re.I), "Федерального казначейства"),
    (re.compile(r"ФЕДЕРАЛЬНАЯ\s+ПРОБИРНАЯ\s+ПАЛАТА", re.I), "Федеральной пробирной палаты"),
)

def _LETTERHEAD_ISSUER(blob: str) -> str:
    """Ведомство из шапки приказа (СТРОЧНЫЕ буквы) — для kind, не identity-claim."""
    for rx, short in _LETTERHEAD:
        if rx.search(blob):
            return short
    return ""

def _LETTERHEAD_ISSUERS(blob: str) -> list[str]:
    """Все ведомства шапки по порядку — совместный приказ."""
    found: list[str] = []
    for rx, short in _LETTERHEAD:
        if rx.search(blob) and short not in found:
            found.append(short)
    return found

def _document_head_member(g: DocGraph) -> Member | None:
    """Шапка ЭТОГО XML. Не filename. Не ближайший акт в seed."""
    paras = _xml_paragraphs(g.source_path)
    if not paras:
        return None
    ms, _ = parse_members(paras[0], "xml-head", None)
    numbered = [m for m in ms if m.number not in {"", "—"} and m.type_name]
    if numbered:
        head = numbered[0]
        head.type_from = "document_head"
        head.type_why = "шапка этого XML (CurrentDocumentRequisites), не чужой акт"
        return head
    blob = "\n".join(paras[:12])
    # Судебный документ: шапка суда или имя файла court_* — head не минтим
    # (оспариваемый акт в тексте — не CurrentDocumentRequisites).
    prikaz_letter = re.search(r"^\s*ПРИКАЗ\s*$", blob, re.M)
    # Суд-документ: шапка суда в первых 600 знаках (АС/ВС/кассация/апелляция/общая
    # юрисдикция) или court_* — head не минтим, ПОКА в шапке нет ПРИКАЗА
    # (приказы Судебного департамента при ВС — акты, а не решения суда).
    court_letter = re.search(
        r"ВЕРХОВН\w*\s+СУД\w*|АРБИТРАЖН\w*\s+СУД\w*|КАССАЦИОНН\w*\s+СУД\w*"
        r"|АПЕЛЛЯЦИОНН\w*\s+СУД\w*|СУД\w*\s+ОБЩЕЙ\s+ЮРИСДИКЦИИ"
        r"|ОБЛАСТН\w*\s+СУД\w*|КРАЕВ\w*\s+СУД\w*|РАЙОНН\w*\s+СУД\w*"
        r"|ГОРОДСК\w*\s+СУД\w*|МИРОВ\w*\s+СУДЬ\w*",
        "\n".join(paras[:3]),
        re.I,
    ) or Path(g.source_path).name.startswith("court_")
    if court_letter and not prikaz_letter:
        return None
    # Международный договор: шапка без даты/N рядом — fail-closed-typed голова.
    if re.search(r"^\s*МЕЖДУНАРОДН\w*\s+ДОГОВОР\w*\s*$", blob, re.M):
        dm = _OT_DUMA_NN.search(blob) or None
        date = "—"
        if dm:
            mm = _MONTHS_RU.get(dm.group(2).casefold())
            if mm:
                date = f"{int(dm.group(1)):02d}.{mm}.{dm.group(3)}"
        form = classify_type("Международный договор", lexicon())
        cls = classify_layers("Международный договор", blob, form)
        head = _member_from_cls(
            date, "—", "Международный договор", "Международный договор",
            "document_head", "xml-head", blob[:80], cls, pos=0
        )
        head.type_from = "document_head"
        head.type_why = (
            "международный договор: ратификация/идентичность вне скоупа "
            "NP-идентификации; дата в шапке отсутствует или не разобрана"
        )
        return head
    # Минюст «Зарегистрировано … N 4878» — provenance, не шапка акта.
    skip = [(h.start(), h.end()) for h in _MINJUST.finditer(blob)]
    hit = None
    for cand in _DUMA_HEAD.finditer(blob):
        if any(s <= cand.start() < e for s, e in skip):
            continue
        hit = cand
        break
    # ФАС/УФАС по шапке документа: РЕШЕНИЕ/ПРЕДПИСАНИЕ/ОПРЕДЕЛЕНИЕ как отдельная строка.
    # Letterhead сильнее цитат в тексте (иначе «постановление Правительства» из абзаца
    # забирает голову у решения ФАС о ценах).
    kw = None
    if re.search(r"антимонопольн", blob, re.I):
        km = re.search(
            r"^\s*(РЕШЕНИЕ|ПРЕДПИСАНИЕ|ОПРЕДЕЛЕНИЕ|ПОСТАНОВЛЕНИЕ)\s*$", blob, re.M
        )
        if km:
            kw = km.group(1)
    # Постановление УФАС — это дело об АП (КоАП); у центральной ФАС такого вида нет,
    # ПОСТАНОВЛЕНИЕ без «УПРАВЛЕНИЕ…» не трогаем (иначе заберём у ПП РФ).
    if kw == "ПОСТАНОВЛЕНИЕ" and not re.search(
        r"управлен\w*\s+федеральн\w*", blob, re.I
    ) and not re.search(r"по\s+делу\s+N", blob, re.I):
        # без «УПРАВЛЕНИЕ…» и без «по делу N» это не акт ФАС — не отбираем у ПП РФ
        kw = None
    if kw:
        issuer = (
            "УФАС России"
            if re.search(r"управлен\w*\s+федеральн\w*", blob, re.I)
            else "ФАС России"
        )
        kind = f"{ {'РЕШЕНИЕ': 'Решение', 'ПРЕДПИСАНИЕ': 'Предписание', 'ОПРЕДЕЛЕНИЕ': 'Определение', 'ПОСТАНОВЛЕНИЕ': 'Постановление'}[kw] } {issuer}"
        if hit is not None:
            day, month, year, num = (
                hit.group(1), hit.group(2).casefold(), hit.group(3), hit.group(4)
            )
            mm = _MONTHS_RU.get(month)
            if not mm:
                return None
            date = f"{int(day):02d}.{mm}.{year}"
        else:
            dm = _OT_DUMA_NN.search(blob)
            mm = _MONTHS_RU.get(dm.group(2).casefold()) if dm else None
            if not mm:
                return None
            date, num = f"{int(dm.group(1)):02d}.{mm}.{dm.group(3)}", "—"
            cm = re.search(r"по\s+делу\s+N\s+([0-9А-ЯA-Z][0-9А-ЯA-Z/н\-.]*)", blob, re.I)
            if cm:
                num = cm.group(1)
        form = classify_type(kind, lexicon())
        cls = classify_layers(kind, blob, form)
        head = _member_from_cls(
            date, num, kind, kind, "document_head", "xml-head", blob[:80], cls, pos=0
        )
        head.type_from = "document_head"
        n_note = (
            "номер дела целиком (точки внутри)"
            if num != "—"
            else "N в шапке нет — дата единственный якорь"
        )
        tail = (
            " по делу об административном правонарушении (КоАП)"
            if kw == "ПОСТАНОВЛЕНИЕ"
            else " по жалобе"
        )
        head.type_why = (
            f"{kw.lower()} ФАС/УФАС{tail} — индивидуальный акт, не НПА; "
            f"{n_note}; dest не выдумываем"
        )
        return head
    if hit is None and prikaz_letter:
        jm = re.search(r"от\s+(\d{1,2})\s+([а-яё]+)\s+(\d{4})\s+г(?:ода|\.)?(?!\s*N)", blob)
        nl = re.findall(r"^\s*N\s+([0-9А-ЯA-Z][0-9А-ЯA-Z/н\-.]*)\s*$", blob, re.M)
        if jm and nl:
            mm = _MONTHS_RU.get(jm.group(2).casefold())
            if mm:
                issuers = _LETTERHEAD_ISSUERS(blob)
                kind = (
                    "Приказ " + " и ".join(issuers)
                    if issuers
                    else "Приказ"
                )
                date = f"{int(jm.group(1)):02d}.{mm}.{jm.group(3)}"
                num = "/".join(nl[:2])
                form = classify_type(kind, lexicon())
                cls = classify_layers(kind, blob, form)
                head = _member_from_cls(
                    date, num, kind, kind, "document_head", "xml-head", blob[:80], cls, pos=0
                )
                head.type_from = "document_head"
                head.type_why = (
                    "совместный приказ: ведомства из шапки, N через «/» "
                    "(каждому ведомству свой номер); dest не выдумываем"
                )
                return head
    fas_head = None
    if hit is None and re.search(r"решен\w*", blob, re.I) and re.search(r"антимонопольн", blob, re.I):
        dm = _OT_DUMA_NN.search(blob)
        if dm:
            mm = _MONTHS_RU.get(dm.group(2).casefold())
            if mm:
                fas_head = f"{int(dm.group(1)):02d}.{mm}.{dm.group(3)}"
    if hit is None and fas_head is None:
        return None
    if hit is not None:
        day, month, year, num = (
            hit.group(1), hit.group(2).casefold(), hit.group(3), hit.group(4)
        )
        mm = _MONTHS_RU.get(month)
        if not mm:
            return None
        date = f"{int(day):02d}.{mm}.{year}"
    else:
        date, num = fas_head, "—"
    kind = "Федеральный закон"
    if re.search(r"национальн\w*\s+стандарт|гост\s+р", blob, re.I):
        # ГОСТ Р: N из _DUMA_HEAD — номер приказа Росстандарта, не стандарта.
        num = "—"
        kind = "ГОСТ Р"
    elif re.search(r"федеральн\w*\s+конституционн\w*", blob, re.I):
        kind = "Федеральный конституционный закон"
    elif prikaz_letter and re.search(r"\bприказ\b", blob, re.I):
        issuer = ""
        if re.search(r"внутренних\s+дел", blob, re.I):
            issuer = " МВД России"
        elif re.search(r"минобрнауки", blob, re.I):
            issuer = " Минобрнауки России"
        else:
            letter = _LETTERHEAD_ISSUER(blob)
            if letter:
                issuer = f" {letter}"
        kind = f"Приказ{issuer}".strip() if issuer else "Приказ"
    elif re.search(r"распоряжени\w*", blob, re.I) and re.search(r"правительств", blob, re.I):
        kind = "распоряжение Правительства РФ"
    elif re.search(r"постановлени\w*", blob, re.I) and re.search(r"правительств", blob, re.I):
        kind = "Постановление Правительства РФ"
    elif re.search(r"указ\w*\s+президента", blob, re.I):
        kind = "Указ Президента РФ"
    elif re.search(r"решен\w*", blob, re.I) and re.search(r"антимонопольн", blob, re.I):
        kind = (
            "Решение УФАС России"
            if re.search(r"управлени\w*\s+федеральн\w*", blob, re.I)
            else "Решение ФАС России"
        )
    elif re.search(r"\bприказ\b", blob, re.I):
        issuer = ""
        if re.search(r"внутренних\s+дел", blob, re.I):
            issuer = " МВД России"
        elif re.search(r"минобрнауки", blob, re.I):
            issuer = " Минобрнауки России"
        else:
            letter = _LETTERHEAD_ISSUER(blob)
            if letter:
                issuer = f" {letter}"
        kind = f"Приказ{issuer}".strip() if issuer else "Приказ"
    form = classify_type(kind, lexicon())
    cls = classify_layers(kind, blob, form)
    head = _member_from_cls(
        date, num, kind, kind, "document_head", "xml-head", blob[:80], cls, pos=0
    )
    head.type_from = "document_head"
    if kind in {"Решение ФАС России", "Решение УФАС России"}:
        n_note = (
            "номер дела целиком (точки внутри)"
            if num != "—"
            else "N в шапке нет — дата решения единственный якорь"
        )
        head.type_why = (
            f"решение ФАС/УФАС по жалобе — индивидуальный акт, не НПА; "
            f"{n_note}; dest не выдумываем"
        )
    elif kind == "ГОСТ Р":
        head.type_why = (
            "национальный стандарт ГОСТ Р: N в шапке — номер приказа "
            "Росстандарта (прованс), не номер стандарта; identity через ИСО-overlay"
        )
    else:
        head.type_why = (
            "шапка этого XML в форме Думы «DD месяц YYYY года N …», "
            "не consultant-строка «от DATE N»; dest не выдумываем"
        )
    return head


def resolve_short_refs(g: DocGraph, members: list[Member]) -> list[Member]:
    """Краткие Закон N / Положение / Правила — только если в ЭТОМ XML есть «далее — …»."""
    aliases = collect_aliases(g)
    extra: list[Member] = []
    by_block: dict[str, list[Member]] = defaultdict(list)
    for m in members:
        by_block[m.block_id].append(m)
    for b in sorted(g.blocks, key=lambda x: x.order):
        local = by_block.get(b.fragment_id, [])
        for hit in SHORT_LAW_N.finditer(b.text):
            if _short_ref_covered(b.text, hit.start(), local + extra):
                continue
            num = hit.group(2).casefold()
            written = re.sub(r"\s+", " ", hit.group(0)).strip()
            target = aliases.get(num) or aliases.get(f"n {num}")
            if target is None:
                for key in _alias_keys(written):
                    if key in aliases:
                        target = aliases[key]
                        break
            if target is None:
                continue  # fail-closed: нет объявления в этом XML — не выдумываем
            extra.append(
                _clone_alias_hit(
                    target,
                    b.fragment_id,
                    b.text[max(0, hit.start() - 8) : hit.end() + 2],
                    hit.start(),
                    written,
                )
            )
        for hit in THIS_REF.finditer(b.text):
            # «настоящего Положения/Кодекса/ФЗ» — этот документ / его приложение, не чужой акт.
            written = re.sub(r"\s+", " ", hit.group(0)).strip()
            folded = written.casefold()
            if "положен" in folded:
                key = "положение"
            elif "правил" in folded:
                key = "правила"
            elif "кодекс" in folded:
                key = "кодекс"
            elif "закон" in folded:
                key = "федеральный закон"
            else:
                continue
            if key == "кодекс":
                codes = [
                    m
                    for m in members + extra
                    if m.type_name
                    and (
                        "кодекс" in m.type_name.casefold()
                        or "коап" in m.type_name.casefold()
                    )
                ]
                local = [m for m in codes if m.block_id == b.fragment_id]
                target = (local or codes or [None])[0]
                if target is None:
                    continue
                extra.append(
                    _clone_alias_hit(
                        target, b.fragment_id, written, hit.start(), written
                    )
                )
                extra[-1].type_from = "this_document_ref"
                extra[-1].type_why = (
                    "«настоящего Кодекса» — кодекс, на который указывает этот XML "
                    "(hlink/написан здесь), не шапка чужого ФЗ"
                )
                continue
            if key == "федеральный закон":
                head = _document_head_member(g)
                if head is not None:
                    extra.append(
                        _clone_alias_hit(
                            head, b.fragment_id, written, hit.start(), written
                        )
                    )
                    extra[-1].type_from = "this_document_ref"
                    extra[-1].type_why = (
                        "«настоящего Федерального закона» — шапка ЭТОГО XML "
                        "(CurrentDocumentRequisites), не ближайший КС/чужой ФЗ"
                    )
                    continue
                form = classify_type("Федеральный закон", lexicon())
                cls = classify_layers("Федеральный закон", b.text, form)
                extra.append(
                    _member_from_cls(
                        "—",
                        "—",
                        "Федеральный закон",
                        written,
                        "this_document_ref",
                        b.fragment_id,
                        written,
                        cls,
                        pos=hit.start(),
                        alias=written,
                    )
                )
                extra[-1].type_from = "this_document_ref"
                extra[-1].type_why = (
                    "«настоящего Федерального закона» — этот документ; "
                    "реквизиты шапки не разобраны, dest не выдумываем"
                )
                continue
            target = aliases.get(key)
            if target is None and key in {"положение", "правила"}:
                annexes = [
                    m
                    for m in members + extra
                    if (m.type_name or "").casefold() == key
                ]
                cited = [m for m in annexes if m.approved_by]
                target = (cited or annexes or [None])[0]
            if target is not None and key in {"положение", "правила"} and target.type_from != "scoped_alias":
                extra.append(
                    _clone_alias_hit(
                        target, b.fragment_id, written, hit.start(), written
                    )
                )
                extra[-1].type_from = "this_document_ref"
                extra[-1].type_why = (
                    "«настоящего Положения/Правил» — приложение ЭТОГО XML; "
                    "цитата через утверждающий акт, Work не склеиваем"
                )
                continue
            if target is None:
                # нет «далее — Положение»: это CurrentDocumentRequisites / this_ref, не цитата
                form = classify_type("положение" if key == "положение" else "правила", lexicon())
                cls = classify_layers(
                    "положение" if key == "положение" else "правила", b.text, form
                )
                extra.append(
                    _member_from_cls(
                        "—",
                        "—",
                        "положение" if key == "положение" else "правила",
                        written,
                        "this_document_ref",
                        b.fragment_id,
                        written,
                        cls,
                        pos=hit.start(),
                        alias=written,
                    )
                )
                extra[-1].type_from = "this_document_ref"
                extra[-1].type_why = (
                    "«настоящего …» — отсылка к ЭТОМУ документу/приложению "
                    "(CurrentDocumentRequisites), не чужой акт и не scoped_alias"
                )
                continue
            extra.append(
                _clone_alias_hit(
                    target, b.fragment_id, written, hit.start(), written
                )
            )
            extra[-1].type_from = "scoped_alias"
        for hit in UKAZANNY.finditer(b.text):
            written = re.sub(r"\s+", " ", hit.group(0)).strip()
            local = [
                m
                for m in members + extra
                if m.block_id == b.fragment_id
                and m.number not in {"", "—"}
                and (m.type_name or "").casefold().startswith("федеральн")
                and 0 <= m.pos < hit.start()
            ]
            if not local:
                continue
            target = max(local, key=lambda m: m.pos)
            extra.append(
                _clone_alias_hit(
                    target, b.fragment_id, written, hit.start(), written
                )
            )
            extra[-1].type_from = "scoped_alias"
            extra[-1].type_why = (
                "«указанного Федерального закона» — ближайший ФЗ с DATE+N "
                "в этом абзаце, не шапка XML и не «настоящего ФЗ»"
            )
    return members + extra


def print_aliases(g: DocGraph) -> None:
    table = collect_aliases(g)
    print()
    print("-" * 72)
    print(f"SCOPED_ALIAS  {g.doc_id}  (D385 «далее — …», несколько актов в одном XML)")
    if not table:
        print("  (нет объявлений)")
        return
    seen: set[int] = set()
    for key, m in table.items():
        ident = id(m)
        if ident in seen:
            continue
        seen.add(ident)
        keys = [k for k, v in table.items() if id(v) == ident]
        print(
            f"  «далее — {m.alias}»  → {m.date} N {m.number}  TYPE={m.type_name!r}  "
            f"B={m.legal_class} F={m.normativity} graph={m.graph}  @{m.block_id}"
        )
        print(f"      ключи: {', '.join(keys)}")
        if m.approved_by:
            print(f"      цитата: утв. {m.approved_by}  (Work приложения ≠ Work утверждающего акта)")
    unbound: list[tuple[str, str]] = []
    for b in sorted(g.blocks, key=lambda x: x.order):
        for hit in DALEE.finditer(b.text):
            wording = re.sub(r"\s+", " ", hit.group(1)).strip()
            if _is_party_alias(wording):
                continue
            if wording.casefold() in {k.casefold() for k in table} or any(
                (m.alias or "").casefold() == wording.casefold() for m in table.values()
            ):
                continue
            unbound.append((b.fragment_id, wording))
    for fid, wording in unbound:
        print(
            f"  «далее — {wording}»  → (нет своего члена)  fail-closed  @{fid}"
        )
        if re.search(r"регламент|документац", wording, re.I):
            print(
                "      named annex / не TYPE утверждающего приказа — dest не выдумываем"
            )


def print_minjust(g: DocGraph) -> None:
    """Регистрация Минюста — provenance приказа, не отдельный акт."""
    hits: list[tuple[str, str, str]] = []
    for b in g.blocks:
        for h in _MINJUST.finditer(b.text):
            if h.group("dmy"):
                date = h.group("dmy")
            else:
                mm = _MONTHS_RU.get((h.group("mon") or "").casefold())
                if not mm:
                    continue
                date = f"{int(h.group('day')):02d}.{mm}.{h.group('year')}"
            hits.append((b.fragment_id, date, h.group("num")))
    if not hits:
        return
    print()
    print("-" * 72)
    print(f"МИНЮСТ  {g.doc_id}  (регистрация — не член, не Work identity)")
    for fid, date, num in hits:
        print(
            f"  {fid}  Зарегистрировано в Минюсте России {date} N {num}  "
            f"— provenance приказа, dest не ищем"
        )


def print_failclosed_shortrefs(g: DocGraph) -> None:
    """«Закон N 44-ФЗ» без «далее — …» в этом XML — не выдумываем алиас."""
    aliases = collect_aliases(g)
    print()
    print("-" * 72)
    print(f"КРАТКИЕ ОТСЫЛКИ  {g.doc_id}  (без объявления в этом XML — fail-closed)")
    n = 0
    members = collect_members(g, with_neighbor=True)
    by_block: dict[str, list[Member]] = defaultdict(list)
    for m in members:
        by_block[m.block_id].append(m)
    for b in sorted(g.blocks, key=lambda x: x.order):
        local = by_block.get(b.fragment_id, [])
        extra = [m for m in members if m.block_id == b.fragment_id and m.type_from == "scoped_alias"]
        for hit in SHORT_LAW_N.finditer(b.text):
            if _short_ref_covered(b.text, hit.start(), local + extra):
                continue
            written = re.sub(r"\s+", " ", hit.group(0)).strip()
            num = hit.group(2)
            resolved = any(
                m.type_from == "scoped_alias" and m.number.casefold() == num.casefold()
                for m in extra
            )
            if resolved:
                continue
            n += 1
            snippet = b.text.strip().replace("\n", " ")[:110]
            print(
                f"  {b.fragment_id}  «{written}»  aliases={len(aliases)}  "
                f"не резолвим (нет «далее — …» в этом XML)"
            )
            print(f"    «{snippet}»")
    if n == 0:
        print("  (нет нерешённых кратких отсылок)")


def print_same_act_repeats(g: DocGraph) -> None:
    members = collect_members(g, with_neighbor=True)
    same = [m for m in members if m.type_from == "same_act_in_document"]
    if not same:
        return
    print()
    print("-" * 72)
    print(f"SAME_ACT  {g.doc_id}  (повтор дата+N, gap≫2, не серия «в ред.»)")
    for m in same:
        print(
            f"  {m.block_id}  {m.date} N {m.number}  TYPE={m.type_name!r}  "
            f"from=same_act_in_document  graph={m.graph}"
        )
        if m.consultant_ref:
            print(f"      consultant {m.consultant_ref[:88]}")
        else:
            print("      consultant: нет dest на этот номер в XML — не выдумываем")


def print_this_refs(g: DocGraph) -> None:
    members = collect_members(g, with_neighbor=True)
    refs = [m for m in members if m.type_from == "this_document_ref"]
    bound = {(m.block_id, (m.alias or "").casefold()) for m in refs}
    unbound: list[tuple[str, str]] = []
    for b in g.blocks:
        for hit in THIS_REF.finditer(b.text):
            written = re.sub(r"\s+", " ", hit.group(0)).strip()
            if (b.fragment_id, written.casefold()) not in bound:
                unbound.append((b.fragment_id, written))
    if not refs and not unbound:
        return
    print()
    print("-" * 72)
    print(f"THIS_DOCUMENT_REF  {g.doc_id}  («настоящего …» — этот XML, не чужой акт)")
    for m in refs:
        dest = "Y" if _dest_kind(m.consultant_ref) == "offline" else "n"
        print(
            f"  {m.block_id}  «{m.alias or m.type_written}»  → {m.date} N {m.number}  "
            f"TYPE={m.type_name!r}  graph={m.graph}  dest={dest}"
        )
        print(f"    {m.type_why}")
    for fid, written in unbound:
        print(f"  {fid}  «{written}»  → (нет якоря в этом XML)  fail-closed")
        if "кодекс" in written.casefold():
            print(
                "    «настоящего Кодекса» не клеим на шапку ФЗ "
                "(правка КоАП ≠ сам КоАП)"
            )


def print_inbound(g: DocGraph) -> None:
    hits = []
    for b in g.blocks:
        for h in INBOUND.finditer(b.text):
            hits.append((b.fragment_id, h.group(0), b.text.strip().replace("\n", " ")[:120]))
    if not hits:
        return
    print()
    print("-" * 72)
    print(f"INBOUND  {g.doc_id}  («вх. …» канцелярия — не член серии, dest не ищем)")
    for fid, span, snippet in hits:
        print(f"  {fid}  {span}")
        print(f"    «{snippet}»")


def print_homographs(graphs: list[DocGraph]) -> None:
    by_num: dict[str, list[tuple[str, str, str | None, str]]] = defaultdict(list)
    for g in graphs:
        seen: set[tuple[str, str]] = set()
        for m in collect_members(g, with_neighbor=True):
            if m.number in {"", "—"}:
                continue
            key = (m.date, m.number.casefold())
            if key in seen:
                continue
            seen.add(key)
            by_num[m.number.casefold()].append((g.doc_id, m.date, m.type_name, m.graph))
    print()
    print("=" * 72)
    print("ОМОГРАФ НОМЕРА  один N ≠ один акт (ключ = дата+N+TYPE)")
    shown = 0
    for num, rows in sorted(by_num.items(), key=lambda kv: -len({(r[1], r[2]) for r in kv[1]})):
        uniq = {(r[1], r[2]) for r in rows}
        if len(uniq) <= 1:
            continue
        shown += 1
        print(f"  N {num}:")
        for doc, date, typ, graph in rows:
            print(f"    {doc:<14} {date}  TYPE={typ!r:40} graph={graph}")
    if shown == 0:
        print("  (нет)")


def print_code_abbrev(graphs: list[DocGraph]) -> None:
    """Pullenti Termin+Acronym KIND=Kodex — ориентация. Не runtime, не UA."""
    print()
    print("=" * 72)
    print("КОДЕКСЫ / СОКРАЩЕНИЯ  Pullenti DecreeToken.Acronym → канон TYPE")
    print("  голый ТК/ВК — омограф, fail-closed. Голый ГК/УК без «РФ» не ловим (чтобы «УК» ⊄ «Минобрнауки»).")
    print(f"  {'акр.':<6} {'канон TYPE':<36} {'полное имя Pullenti':<44} в seed")
    found: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for g in graphs:
        seen: set[str] = set()
        for m in collect_members(g, with_neighbor=True):
            if not m.type_name:
                continue
            key = m.type_name.casefold()
            if key in seen:
                continue
            seen.add(key)
            found[key].append((g.doc_id, m.block_id))
    for acr, canon, full in CODE_ABBREV:
        hits = found.get(canon.casefold(), [])
        where = ", ".join(f"{d}:{b}" for d, b in hits[:3]) if hits else "—"
        print(f"  {acr:<6} {canon:<36} {full:<44} {where}")
    refuse = []
    for g in graphs:
        for m in collect_members(g, with_neighbor=True):
            if (m.type_name or "").casefold() in {"тк", "тк рф", "вк", "вк рф"}:
                refuse.append((g.doc_id, m.type_name, m.graph))
    print()
    print("  омограф ТК/ВК в seed (должны быть пусто / refuse):")
    if not refuse:
        print("    (нет голых ТК/ВК — правильно)")
    for doc, typ, graph in refuse:
        print(f"    {doc}  TYPE={typ!r}  graph={graph}")


def print_procurement_laws(graphs: list[DocGraph]) -> None:
    """44-ФЗ ≠ 223-ФЗ. Заголовок без N не клеим на канон."""
    print()
    print("=" * 72)
    print("ЗАКУПКИ  два разных ФЗ (не омограф номера; 223-ФЗ в seed нет — dest не выдумываем)")
    print(f"  {'N':<8} {'дата':<12} {'канон':<22} в seed / заголовок без N")
    by_num: dict[str, list[tuple[str, str]]] = defaultdict(list)
    titles: list[tuple[str, str, str]] = []
    for g in graphs:
        seen: set[str] = set()
        members = collect_members(g, with_neighbor=True)
        for m in members:
            num = (m.number or "").upper()
            if num in {"44-ФЗ", "223-ФЗ"} and num not in seen:
                seen.add(num)
                by_num[num].append((g.doc_id, m.block_id))
        for b in g.blocks:
            for h in _PROCURE_TITLE.finditer(b.text):
                span = re.sub(r"\s+", " ", h.group(0)).strip()
                folded = span.casefold()
                canon = "223-ФЗ" if "отдельными" in folded else "44-ФЗ"
                numbered = any(
                    m.block_id == b.fragment_id and (m.number or "").upper() == canon
                    for m in members
                )
                titles.append((g.doc_id, b.fragment_id, canon if numbered else f"{canon}? без N"))
    for num, date, kind, title in PROCUREMENT_LAW:
        hits = by_num.get(num, [])
        where = ", ".join(f"{d}:{b}" for d, b in hits[:3]) if hits else "— (в seed нет)"
        print(f"  {num:<8} {date:<12} {kind:<22} {where}")
        print(f"           {title}")
    unnamed = [row for row in titles if "без N" in row[2]]
    if unnamed:
        print()
        print("  заголовок без номера (не клеим на канон):")
        for doc, fid, note in unnamed:
            print(f"    {doc} {fid}  {note}  — fail-closed, dest не выдумываем")


def print_code_parts(g: DocGraph) -> None:
    """Pullenti DECREEPART: ст./ч. на кодексе, включая диапазон. Не идентичность акта."""
    hits: list[tuple[str, str, str, str, str]] = []
    covered: set[tuple[str, int]] = set()
    for b in g.blocks:
        for h in CODE_PART.finditer(b.text):
            art = h.group("article") or ""
            part = h.group("part") or ""
            code = (h.group("code") or "").upper()
            span = re.sub(r"\s+", " ", h.group(0)).strip()
            if len(span) < 6:
                continue
            hits.append((b.fragment_id, span, art, part, code))
            covered.add((b.fragment_id, h.start()))
        for h in CODE_PART_BARE.finditer(b.text):
            if any(fid == b.fragment_id and abs(h.start() - pos) < 8 for fid, pos in covered):
                continue
            if CODE_PART.search(b.text[max(0, h.start() - 4) : h.end() + 40]):
                continue
            span = re.sub(r"\s+", " ", h.group(0)).strip()
            if len(span) < 8:
                continue
            hits.append(
                (b.fragment_id, span, "", h.group("part") or "", "")
            )
    if not hits:
        return
    print()
    print("-" * 72)
    print(f"DECREEPART  {g.doc_id}  (ст./ч. на кодексе — диагностика, не Work identity)")
    for fid, span, art, part, code in hits:
        canon = ""
        if code:
            for acr, c, _full in CODE_ABBREV:
                if acr == code:
                    canon = c
                    break
        extra = f" ч./п.={part}" if part else ""
        print(
            f"  {fid}  «{span}»  ст.={art}{extra}  code={code or '—'}  "
            f"TYPE={canon or '—'}  (не отдельный акт)"
        )


def print_standards(g: DocGraph) -> None:
    """ГОСТ/ИСО/ТР ТС/СНиП — overlay. Голый ТР не ловим."""
    members = [
        m
        for m in collect_members(g, with_neighbor=True)
        if m.type_name and _ISO_STD.search(m.type_name)
    ]
    raw: list[tuple[str, str]] = []
    for b in g.blocks:
        for h in _ISO_STD.finditer(b.text):
            raw.append((b.fragment_id, re.sub(r"\s+", " ", h.group(0)).strip()))
    if not members and not raw:
        return
    print()
    print("-" * 72)
    print(f"СТАНДАРТ / ТР  {g.doc_id}  (не Work identity; голый ТР ⊄ «третье»)")
    seen: set[str] = set()
    for m in members:
        key = f"{m.block_id}|{m.type_name}"
        if key in seen:
            continue
        seen.add(key)
        print(
            f"  {m.block_id}  TYPE={m.type_name!r}  C={m.competence}  "
            f"graph={m.graph}  from={m.type_from}"
        )
    for fid, span in raw:
        if not any(span.casefold() in (m.type_name or "").casefold() for m in members):
            print(f"  {fid}  «{span}»  (написано, член не собран)")


def print_not_acts(g: DocGraph) -> None:
    """ЕИС/ИНН/КТРУ/МНН — закупки и медицина, не акт."""
    hits: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for b in g.blocks:
        for h in _NOT_ACT.finditer(b.text):
            token = h.group(1).upper()
            key = (b.fragment_id, token)
            if key in seen:
                continue
            seen.add(key)
            hits.append((b.fragment_id, token))
        if _KTRU.search(b.text):
            key = (b.fragment_id, "КТРУ")
            if key not in seen:
                seen.add(key)
                hits.append((b.fragment_id, "КТРУ"))
        if _EIS.search(b.text):
            key = (b.fragment_id, "ЕИС")
            if key not in seen:
                seen.add(key)
                hits.append((b.fragment_id, "ЕИС"))
    if not hits:
        return
    members = collect_members(g, with_neighbor=True)
    print()
    print("-" * 72)
    print(f"НЕ АКТ  {g.doc_id}  (закупки/медицина/рег.номер — не TYPE)")
    for fid, token in hits:
        why = _NOT_ACT_WHY.get(token, "идентификатор/платформа/классификатор, не член")
        extra = ""
        if token in _PLATFORM_ACT:
            date, num, kind = _PLATFORM_ACT[token]
            local = [
                m
                for m in members
                if m.block_id == fid
                and (
                    m.number == num
                    or (
                        token == "КТРУ"
                        and (m.type_name or "").casefold() == "правила"
                    )
                )
            ]
            if local:
                bits = []
                for m in local:
                    if m.number == num:
                        bits.append(f"утв. {m.date} N {m.number}")
                    elif (m.type_written or "").casefold().startswith("правил"):
                        bits.append(m.type_written)
                extra = "  → " + "; ".join(bits)
            else:
                extra = (
                    f"  → в этом XML нет {kind} от {date} N {num} "
                    f"— dest не выдумываем"
                )
        print(f"  {fid}  {token}  — {why}{extra}")


def collect_members(g: DocGraph, *, with_neighbor: bool) -> list[Member]:
    members: list[Member] = []
    seen: set[tuple[str, str, str]] = set()
    same_act = _same_act_index(g) if with_neighbor else {}
    for b in sorted(g.blocks, key=lambda x: x.order):
        inherited = _inherited_type_for(g, b.fragment_id) if with_neighbor else None
        from_same_act = False
        from_xml_adj = False
        if inherited is None and with_neighbor:
            # повтор той же цитаты в другом абзаце (051→052), не continues_series
            probe, _ = parse_members(b.text, b.fragment_id, None)
            for m in probe:
                if not m.type_name and (m.date, m.number) in same_act:
                    inherited = same_act[(m.date, m.number)]
                    from_same_act = True
                    break
            if inherited is None and b.starts_ot_tail:
                # сирота seed: голова в предыдущем w:p XML (012: «с изм., внесенными … КС РФ»)
                xml_type = _xml_neighbor_head(g, b)
                if xml_type:
                    inherited = xml_type
                    from_xml_adj = True
        ms, _ = parse_members(b.text, b.fragment_id, inherited)
        for m in ms:
            if from_same_act and m.type_from == "inherited_from_series_head":
                m.type_from = "same_act_in_document"
            if from_xml_adj and m.type_from == "inherited_from_series_head":
                m.type_from = "xml_adjacent_block"
            annex_w = (
                (m.type_written or "")[:48]
                if (m.type_name or "").casefold()
                in {
                    "положение",
                    "правила",
                    "конкурсная документация",
                    "методические рекомендации",
                    "регламент",
                    "перечень",
                    "порядок",
                }
                else ""
            )
            key = (m.block_id, m.date, m.number, m.type_name or "", annex_w)
            if key in seen:
                continue
            seen.add(key)
            members.append(m)
    if with_neighbor:
        for chain in series_chains(g):
            last = g.by_id()[chain[-1]]
            if not (last.starts_ot_tail and last.ends_open):
                continue
            inherited = _inherited_type_for(g, last.fragment_id)
            extra = _xml_forward_tails(g, last, inherited)
            for m in extra:
                key = (m.block_id, m.date, m.number, m.type_name or "")
                if key in seen:
                    continue
                seen.add(key)
                members.append(m)
        members = attach_consultant(g, members)
        members = attach_seed_hlink_members(g, members)
        members = resolve_short_refs(g, members)
        # «далее — X» на финальных членах: 035 «Закон о защите конкуренции» → 135-ФЗ.
        by_block: dict[str, list[Member]] = defaultdict(list)
        for m in members:
            if m.type_from not in {"this_document_ref", "scoped_alias"}:
                by_block[m.block_id].append(m)
        for b in sorted(g.blocks, key=lambda x: x.order):
            local = by_block.get(b.fragment_id, [])
            for hit in DALEE.finditer(b.text):
                wording = re.sub(r"\s+", " ", hit.group(1)).strip()
                if _is_party_alias(wording):
                    continue
                target = _nearest_member(local, hit.start(), wording)
                if target is not None and not target.alias:
                    target.alias = wording
        aliases = collect_aliases(g)
        for m in members:
            if m.alias or m.number in {"", "—"}:
                continue
            target = aliases.get(m.number.casefold()) or aliases.get(f"n {m.number.casefold()}")
            if target is not None and target.number == m.number:
                m.alias = target.alias or target.type_written or ""
        # Реквизиты-без-типа в цитатах-правках («после слов/слова "от DATE N"»):
        # семейство акта берём из шапки ЭТОГО документа (правки ПП цитируют ПП).
        head = _document_head_member(g)
        hf = (head.type_name or "") if head is not None and head.number not in {"", "—"} else ""
        if hf in {
            "Постановление Правительства РФ",
            "распоряжение Правительства РФ",
            "Указ Президента РФ",
            "Федеральный закон",
        }:
            for m in members:
                if m.type_name is None and m.type_from == "missing" and m.number not in {"", "—"}:
                    form = classify_type(hf, lexicon())
                    cls = classify_layers(hf, m.snippet or "", form)
                    m.type_name = hf
                    m.type_written = m.type_written or hf
                    m.type_bucket = cls["bucket"]
                    m.type_verdict = cls["verdict"]
                    m.graph = cls["graph"]
                    m.legal_class = cls["legal_class"]
                    m.competence = cls["competence"]
                    m.issuer = cls["issuer"]
                    m.normativity = cls["normativity"]
                    m.binding = cls["binding"]
                    m.admin = cls["admin"]
                    m.identity_key = cls["identity_key"]
                    m.type_why = (
                        "реквизиты без типа (цитата-правка «после слов/слова»); "
                        f"семейство унаследовано от шапки документа ({hf})"
                    )
    return members


def print_breaks(graphs: list[DocGraph]) -> None:
    print()
    print("=" * 72)
    print("ОБРЫВЫ  continues_series vs сирота vs ложный OPEN")
    print("  ребро: gap<=2 AND голова ends_open AND хвост starts_ot_tail")
    print("  сирота: «от DATE N» без головы в seed — не подставляем шапку XML")
    n_chain = n_closed = n_orphan = n_false_open = 0
    for g in graphs:
        chains = series_chains(g)
        in_series: set[str] = set()
        for ch in chains:
            in_series.update(ch)
        a_members = collect_members(g, with_neighbor=False)
        b_members = collect_members(g, with_neighbor=True)
        a_by = defaultdict(list)
        b_by = defaultdict(list)
        for m in a_members:
            a_by[m.block_id].append(m)
        for m in b_members:
            b_by[m.block_id].append(m)
        if chains:
            print()
            print(f"  {g.doc_id}  цепочек={len(chains)}")
            for ch in chains:
                n_chain += 1
                print(f"    {' → '.join(ch)}")
                for fid in ch:
                    blk = g.by_id()[fid]
                    snippet = blk.text.strip().replace("\n", " ")[:90]
                    am = a_by.get(fid, [])
                    bm = b_by.get(fid, [])
                    a_miss = [m for m in am if not m.type_name]
                    b_got = [m for m in bm if m.type_name and m.type_from == "inherited_from_series_head"]
                    n_closed += len(b_got)
                    flag = []
                    if blk.ends_open:
                        flag.append("OPEN")
                    if blk.starts_ot_tail:
                        flag.append("TAIL")
                    print(f"      {fid}  {' '.join(flag):10} «{snippet}»")
                    if a_miss and b_got:
                        nums = ", ".join(m.number for m in b_got)
                        print(
                            f"        А: без TYPE ({len(a_miss)})  "
                            f"Б: TYPE={b_got[0].type_name!r}  N {nums}  "
                            f"graph={b_got[0].graph}"
                        )
                    elif not a_miss:
                        print("        голова: TYPE написан здесь")
                    if blk.starts_ot_tail and blk.ends_open and fid == ch[-1]:
                        print(
                            "        seed_truncated: последний хвост в seed кончается запятой; "
                            "TYPE с головы серии, закрывающую скобку не выдумываем"
                        )
                        fwd = [
                            m
                            for m in b_members
                            if m.type_from == "xml_adjacent_tail"
                            and str(m.block_id).startswith(f"xml-fwd:{fid}")
                        ]
                        if fwd:
                            n_closed += len(fwd)
                            nums = ", ".join(m.number for m in fwd)
                            print(
                                f"        + {len(fwd)} из следующего w:p XML: "
                                f"TYPE={fwd[0].type_name!r}  N {nums}  "
                                f"from=xml_adjacent_tail"
                            )
        orphans = [
            b
            for b in g.blocks
            if b.starts_ot_tail and b.fragment_id not in in_series
        ]
        if orphans:
            print()
            print(f"  {g.doc_id}  «от DATE N» вне серии:")
            for b in orphans:
                snippet = b.text.strip().replace("\n", " ")[:90]
                bm = b_by.get(b.fragment_id, [])
                same = [m for m in bm if m.type_from == "same_act_in_document"]
                adj = [m for m in bm if m.type_from == "xml_adjacent_block"]
                print(f"      {b.fragment_id} #{b.order}  «{snippet}»")
                if same:
                    print(
                        f"        повтор того же акта в XML: TYPE={same[0].type_name!r}  "
                        f"from=same_act_in_document  (не серия «в ред.»)"
                    )
                    continue
                if adj:
                    n_closed += len(adj)
                    print(
                        f"        соседний w:p источника: TYPE={adj[0].type_name!r}  "
                        f"B={adj[0].legal_class} graph={adj[0].graph}  "
                        f"from=xml_adjacent_block  (не шапка XML)"
                    )
                    continue
                n_orphan += 1
                am = a_by.get(b.fragment_id, [])
                for m in am:
                    print(
                        f"        fail-closed: {m.date} N {m.number}  TYPE={m.type_name!r}  "
                        f"graph={m.graph}  from={m.type_from}"
                    )
                print("        сирота: голова не в seed и не в 1–2 соседних w:p — шапку XML не подставляем")
        false_open = [
            b
            for b in g.blocks
            if b.ends_open and b.fragment_id not in in_series
        ]
        for b in false_open:
            n_false_open += 1
    print()
    print(
        f"  итог: цепочек={n_chain}  хвостов закрыто членами={n_closed}  "
        f"сирот={n_orphan}  OPEN без серии={n_false_open}"
    )


def print_chain_cards(g: DocGraph) -> None:
    """Каждый номер серии — отдельная карточка + consultantplus://. Не Work identity."""
    chains = series_chains(g)
    members = collect_members(g, with_neighbor=True)
    numbered = _uniq_numbered(members)
    if not chains and not numbered:
        return
    print()
    print("-" * 72)
    print(f"ЦЕПОЧКА ПО НОМЕРАМ  {g.doc_id}  (один акт = один номер, dest если Консультант дал)")
    if chains:
        shown: set[tuple[str, str]] = set()
        for i, ch in enumerate(chains):
            print(f"  seed: {' → '.join(ch)}")
            if i > 0:
                print("    (повтор той же серии в другом абзаце — номера те же)")
            by_block: dict[str, list[Member]] = defaultdict(list)
            for m in members:
                by_block[m.block_id].append(m)
            n = 0
            for fid in ch:
                for m in by_block.get(fid, []):
                    if m.number in {"", "—"}:
                        continue
                    key = (m.date, m.number.casefold())
                    if key in shown:
                        continue
                    shown.add(key)
                    n += 1
                    _print_card(n, m)
            fwd = [
                m
                for m in members
                if m.type_from == "xml_adjacent_tail"
                and str(m.block_id).startswith("xml-fwd:")
            ]
            for m in fwd:
                key = (m.date, m.number.casefold())
                if key in shown:
                    continue
                shown.add(key)
                n += 1
                _print_card(n, m)
    else:
        n = 0
        for m in numbered:
            n += 1
            _print_card(n, m)
    annexes = [
        m
        for m in members
        if m.number in {"", "—"}
        and m.approved_by
        and m.type_from not in {"this_document_ref", "scoped_alias"}
    ]
    seen_ann: set[str] = set()
    k = 0
    for m in annexes:
        # один named annex = одна карточка (повтор цитаты в другом абзаце не дублируем);
        # разные written (Правилами ведения / формирования) остаются разными карточками.
        key = f"{m.type_name}|{m.type_written}|{m.approved_by}"
        if key in seen_ann:
            continue
        seen_ann.add(key)
        k += 1
        print(
            f"  annex {k:02d}. TYPE={m.type_name!r}  N —  B={m.legal_class}  "
            f"F={m.normativity}  graph={m.graph}"
        )
        print(f"      цитата: утв. {m.approved_by}  (Work приложения ≠ Work утверждающего акта)")


def _print_card(n: int, m: Member) -> None:
    print(
        f"  {n:02d}. {m.date}  N {m.number}  TYPE={m.type_name!r}  "
        f"B={m.legal_class}  graph={m.graph}  from={m.type_from}"
    )
    if m.approved_by:
        print(f"      цитата: утв. {m.approved_by}")
    if m.consultant_ref:
        print(f"      consultant {m.consultant_ref}")
        if m.consultant_tip:
            print(f"      tip: {m.consultant_tip[:160]}")
    else:
        print("      consultant: нет w:hlink в этом XML — dest не выдумываем")


def _uniq_numbered(members: list[Member]) -> list[Member]:
    seen: set[tuple[str, str]] = set()
    uniq: list[Member] = []
    for m in members:
        if m.number in {"", "—"}:
            continue
        key = (m.date, m.number.casefold())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(m)
    return uniq


def _dest_kind(ref: str) -> str:
    if ref.startswith("consultantplus-internal://"):
        return "internal"
    if ref.startswith("consultantplus://"):
        return "offline"
    return "none"


def print_dest_dashboard(graphs: list[DocGraph]) -> None:
    print()
    print("=" * 72)
    print("DEST  consultantplus://offline/ref = dest акта; internal:// = якорь абзаца")
    print(f"  {'doc':<14} {'mem':>4} {'offline':>7} {'internalXML':>11} {'chain':>5} {'missT':>5}  без dest (первые)")
    for g in graphs:
        ms = _uniq_numbered(collect_members(g, with_neighbor=True))
        offline = sum(1 for m in ms if _dest_kind(m.consultant_ref) == "offline")
        miss_t = sum(1 for m in ms if not m.type_name)
        n_chain = len(series_chains(g))
        internal_xml = sum(
            1
            for _vis, dest, _tip in _xml_hlinks(g.source_path)
            if dest.startswith("consultantplus-internal://")
        )
        without = [m for m in ms if _dest_kind(m.consultant_ref) != "offline"]
        miss = ", ".join(f"N {m.number}" for m in without[:4]) if without else "—"
        print(
            f"  {g.doc_id:<14} {len(ms):>4} {offline:>7} {internal_xml:>11} "
            f"{n_chain:>5} {miss_t:>5}  {miss}"
        )
    # Кодексы без N: identity по имени, DATE+N=—, в DEST не участвуют.
    rows: list[str] = []
    for g in graphs:
        codes = [
            m
            for m in collect_members(g, with_neighbor=True)
            if m.number in {"", "—"}
            and m.type_name
            and (
                "кодекс" in m.type_name.casefold()
                or m.type_name.casefold() in _CODE_ABBREV_CANONS
                or any(
                    m.type_name.casefold().startswith(stem)
                    for stem in _CODE_ABBREV_STEMS
                )
            )
        ]
        if not codes:
            continue
        agg: dict[str, int] = {}
        for m in codes:
            agg[m.type_name] = agg.get(m.type_name, 0) + 1
        names = ", ".join(
            f"{name} ×{n}" if n > 1 else name for name, n in agg.items()
        )
        rows.append(f"  {g.doc_id}: {names}")
    if rows:
        print()
        print(
            "  КОДЕКСЫ БЕЗ N  (identity по имени, DATE+N=—; "
            "в DEST не участвуют, N не выдумываем)"
        )
        for r in rows:
            print(r)


def print_consultant_coverage(g: DocGraph) -> None:
    uniq = _uniq_numbered(collect_members(g, with_neighbor=True))
    with_dest = [m for m in uniq if _dest_kind(m.consultant_ref) == "offline"]
    without = [m for m in uniq if m not in with_dest]
    internal_xml = sum(
        1
        for _vis, dest, _tip in _xml_hlinks(g.source_path)
        if dest.startswith("consultantplus-internal://")
    )
    print()
    print(
        f"  CONSULTANT {g.doc_id}: dest_offline={len(with_dest)}/{len(uniq)}  "
        f"internal_xml={internal_xml} (якорь абзаца, не dest акта)"
    )
    if without:
        miss = ", ".join(f"N {m.number}" for m in without[:12])
        print(f"    без dest акта: {miss}")


def print_doc_layers(g: DocGraph) -> None:
    print()
    print("=" * 72)
    print(f"СЛОИ  {g.doc_id}  xml=…/{Path(g.source_path).name}")
    print_member_table(collect_members(g, with_neighbor=True), "ветка Б (сосед по серии + оси D516):")


def print_control(graphs: list[DocGraph]) -> None:
    print()
    print("=" * 72)
    print("КОНТРОЛЬ  ветка А (один w:p) vs ветка Б (голова серии) vs оси")
    orphan_a = orphan_b = 0
    series_n = 0
    old_npa = new_npa = new_hold = new_overlay = new_refuse = 0
    closed: list[tuple[Member, str]] = []
    changed: list[tuple[str, str, str, str, str]] = []
    seen_change: set[tuple[str, str, str]] = set()
    ids_text: dict[str, str] = {}
    for g in graphs:
        for b in g.blocks:
            ids_text[b.fragment_id] = b.text.strip().replace("\n", " ")
        a_members = collect_members(g, with_neighbor=False)
        b_members = collect_members(g, with_neighbor=True)
        b_by = {(m.block_id, m.date, m.number): m for m in b_members}
        in_series: set[str] = set()
        for chain in series_chains(g):
            in_series.update(chain)
        for m in a_members:
            partner = b_by.get((m.block_id, m.date, m.number))
            if m.block_id in in_series:
                series_n += 1
                if not m.type_name:
                    orphan_a += 1
                if partner and not partner.type_name:
                    orphan_b += 1
                if (not m.type_name) and partner and partner.type_name:
                    closed.append((partner, ids_text.get(m.block_id, "")))
            shown = partner or m
            form = classify_type(m.type_name, lexicon())
            old = (
                "identifying_act"
                if form.get("bucket") in {
                    "federal",
                    "presidential",
                    "government",
                    "agency",
                    "court",
                }
                else "refuse"
            )
            new = shown.graph
            if old == "identifying_act":
                old_npa += 1
            if new == "identifying_act":
                new_npa += 1
            elif new == "hold":
                new_hold += 1
            elif new == "overlay":
                new_overlay += 1
            else:
                new_refuse += 1
            ch = (shown.type_name or "", old, new, shown.legal_class)
            if shown.type_name and old != new and ch not in seen_change:
                seen_change.add(ch)
                changed.append((*ch, shown.block_id))
    print(f"  членов дата+N в сериях: {series_n}")
    print(f"  без TYPE в своём абзаце (А): {orphan_a}")
    print(f"  без TYPE после соседа (Б):   {orphan_b}")
    print(f"  обрывов закрыто: {orphan_a - orphan_b}")
    print(f"  старый рубильник → граф НПА (все члены): {old_npa}")
    print(
        f"  оси: identifying_act={new_npa}  hold={new_hold}  "
        f"overlay={new_overlay}  refuse={new_refuse}"
    )
    print()
    print("  закрытые хвосты серии (живой абзац, все, не первые 8):")
    if not closed:
        print("    (нет)")
    for m, text in closed:
        print(f"    {m.block_id}  «{text[:110]}»")
        print(
            f"      А: нет TYPE, refuse «неизвестно N {m.number}»")
        print(
            f"      Б: TYPE={m.type_name!r}  B={m.legal_class}  "
            f"graph={m.graph}  from={m.type_from}"
        )
    print()
    print("  смена ребра (уникальные каноны):")
    if not changed:
        print("    (нет)")
    for typ, old, new, cls, bid in changed:
        print(f"    {typ!r:42} {old:16} → {new:16}  B={cls}  ({bid})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc", default=None, help="например npa-doc-020")
    parser.add_argument(
        "--on",
        default=None,
        help="fragment_id, с которого начать шаги (по умолчанию хвосты серий)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="только оси D516 и таблица членов, без простыни графа",
    )
    args = parser.parse_args()
    graphs = load_docs(ROOT, args.doc)
    print_layer_matrix()
    if args.compact:
        print_dest_dashboard(graphs)
        print_control(graphs)
        print_homographs(graphs)
        print_code_abbrev(graphs)
        print_procurement_laws(graphs)
        # Эта итерация: свежий корпус (npa/fas/courts) через парсер.
        cards = {
            "npa-doc-035",
            "npa-doc-036",
            "npa-doc-038",
        }
        print_breaks(graphs)
        for g in graphs:
            print_this_refs(g)
            print_inbound(g)
            print_code_parts(g)
            print_standards(g)
            print_minjust(g)
            if g.doc_id in {"npa-doc-022", "npa-doc-027", "npa-doc-028", "npa-doc-030"}:
                print_not_acts(g)
            if g.doc_id in {"npa-doc-014", "npa-doc-015", "npa-doc-032", "npa-doc-035"}:
                print_aliases(g)
            if g.doc_id in cards:
                print_consultant_coverage(g)
                print_chain_cards(g)
                print_doc_layers(g)
        return 0
    print_idea_matrix()
    print_dataflow()
    for g in graphs:
        print_graph(g)
        print_doc_layers(g)
        if args.on:
            if args.on in g.by_id():
                walk_example(g, args.on)
        else:
            chains = series_chains(g)
            shown = set()
            for ch in chains:
                walk_example(g, ch[-1])
                shown.add(ch[-1])
            for b in g.blocks:
                if not b.ends_open and not b.starts_ot_tail and b.fragment_id not in shown:
                    if ED_NOTE.match(b.text) and "Указа" in b.text or "Постановления" in b.text:
                        walk_example(g, b.fragment_id)
                        break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Russian legal citation value object.

[proposed] D046 domain form — fields + basic validation only, no logic.
Materialises the R035/R038 citation contract as a Pydantic data shape; it is
NOT validation proof until real parser data hardens the forms.

Models the Russian citation hierarchy ст / ч / п / подп / абз:

- ст  (статья)    — article
- ч   (часть)     — part
- п   (пункт)     — point
- подп (подпункт) — subpoint
- абз (абзац)     — paragraph / indent

Values are kept as strings because Russian legal numbering is heterogeneous
(composite numbers like "34.1", roman numerals, lettered subpoints "а"/"б").
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class Citation(BaseModel):
    """Pointer into a legal act by structural coordinates.

    At least one coordinate MUST be set. ``article`` is the usual anchor; the
    remaining coordinates narrow the location within the article.
    """

    model_config = ConfigDict(extra="forbid")

    article: str | None = None
    part: str | None = None
    point: str | None = None
    subpoint: str | None = None
    paragraph: str | None = None

    @model_validator(mode="after")
    def _at_least_one_coordinate(self) -> Self:
        if not any(
            value
            for value in (
                self.article,
                self.part,
                self.point,
                self.subpoint,
                self.paragraph,
            )
        ):
            msg = (
                "Citation requires at least one coordinate (article/part/point/subpoint/paragraph)"
            )
            raise ValueError(msg)
        return self

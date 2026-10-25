#!/usr/bin/env python3
"""Independent XML oracle for the ln-decode source-package pin (control harness).

This is evidence tooling, NOT product code. It shares no parsing logic with
`crates/ln-decode/src/source_package.rs` (quick-xml + hand-written slot
assembly). It re-derives the decoded ElementTree-style `text`/`tail` slot
sequence of one tracked WordML fixture with two independent Python XML
front-ends, then emits the exact length-prefixed SHA-256 that the Rust
acceptance test pins:

  H = sha256( concat( u64be(len(p)) || utf8(p) for p in (owner, slot, value) ) )

Agreement is parity between two XML implementations over the same bounded
fixture. It is not legal-accuracy, coverage, or authenticity evidence.

Usage:
  python3 source_package_oracle.py <fixture.xml>
"""

import hashlib
import struct
import sys
import xml.etree.ElementTree as ElementTree
import xml.parsers.expat


def _slot_hash(records):
    h = hashlib.sha256()
    text_bytes = 0
    for owner, slot, value in records:
        raw = value.encode("utf-8")
        text_bytes += len(raw)
        for part in (owner, slot, value):
            pb = part.encode("utf-8")
            h.update(struct.pack(">Q", len(pb)))
            h.update(pb)
    return {
        "slots": len(records),
        "text_bytes": text_bytes,
        "slot_hash": h.hexdigest(),
    }


def _expat_slots(path):
    """Event-reader assembly: element frames carry text/tail buffers."""

    class Node:
        __slots__ = ("id", "text", "tail", "children")

        def __init__(self, node_id):
            self.id = node_id
            self.text = ""
            self.tail = ""
            self.children = []

    nodes = []
    stack = []
    parser = xml.parsers.expat.ParserCreate()

    def start(_name, _attrs):
        node = Node("e%d" % len(nodes))
        nodes.append(node)
        if stack:
            stack[-1].children.append(node)
        stack.append(node)

    def char_data(data):
        if not stack:
            return  # document-level whitespace: outside the carried text scope
        top = stack[-1]
        if top.children:
            top.children[-1].tail += data
        else:
            top.text += data

    def end(_name):
        stack.pop()

    parser.StartElementHandler = start
    parser.CharacterDataHandler = char_data
    parser.EndElementHandler = end
    with open(path, "rb") as handle:
        parser.ParseFile(handle)

    records = []

    def walk(node):
        if node.text:
            records.append((node.id, "text", node.text))
        for child in node.children:
            walk(child)
            if child.tail:
                records.append((child.id, "tail", child.tail))

    if nodes:
        walk(nodes[0])
    return len(nodes), records


def _elementtree_slots(path):
    """Tree assembly: ElementTree's own text/tail model, same walk order."""
    tree = ElementTree.parse(path)
    root = tree.getroot()
    order = []
    for index, node in enumerate(root.iter()):
        order.append(node)
    ids = {id(node): "e%d" % index for index, node in enumerate(order)}
    records = []

    def walk(node):
        if node.text:
            records.append((ids[id(node)], "text", node.text))
        for child in node:
            walk(child)
            if child.tail:
                records.append((ids[id(child)], "tail", child.tail))

    walk(root)
    return len(order), records


def main():
    path = sys.argv[1]
    expat_elements, expat_records = _expat_slots(path)
    et_elements, et_records = _elementtree_slots(path)

    print("expat_elements=%d" % expat_elements)
    print("expat_slots=%d" % expat_records.__len__())
    expected = _slot_hash(expat_records)
    print("expat_text_bytes=%d" % expected["text_bytes"])
    print("expat_slot_hash=%s" % expected["slot_hash"])

    tree = _slot_hash(et_records)
    print("elementtree_elements=%d" % et_elements)
    print("elementtree_slots=%d" % tree["slots"])
    print("elementtree_text_bytes=%d" % tree["text_bytes"])
    print("elementtree_slot_hash=%s" % tree["slot_hash"])

    agree = (
        expat_elements == et_elements
        and expected["slots"] == tree["slots"]
        and expected["text_bytes"] == tree["text_bytes"]
        and expected["slot_hash"] == tree["slot_hash"]
    )
    print("oracle_agreement=%s" % ("true" if agree else "false"))
    if not agree:
        sys.exit(1)


if __name__ == "__main__":
    main()

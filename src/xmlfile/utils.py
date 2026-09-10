"""Small internal helpers shared by the parser and the writer.

Nothing here interprets XML content scientifically. These functions only deal
with XML lexical concerns: escaping, and classifying whitespace-only text.
"""

from __future__ import annotations

__all__ = [
    "escape_text",
    "escape_attribute",
    "is_insignificant_whitespace",
]


def escape_text(text: str) -> str:
    """Escape a string for use as element text.

    Only what the XML specification requires is escaped: ``&``, ``<``, and
    ``>`` where it would close a CDATA section. `xml.etree.ElementTree`
    additionally escapes every ``>``, which would needlessly alter files that
    contain a literal ``>`` in their text.
    """
    text = text.replace("&", "&amp;").replace("<", "&lt;")
    return text.replace("]]>", "]]&gt;")


def escape_attribute(value: str) -> str:
    """Escape a string for use as a double-quoted attribute value.

    Newlines, tabs and carriage returns are escaped as character references
    because an XML processor is otherwise permitted to normalise them to
    spaces, which would silently corrupt multi-line attribute values.
    """
    value = value.replace("&", "&amp;").replace("<", "&lt;")
    value = value.replace('"', "&quot;")
    value = value.replace("\r", "&#13;").replace("\n", "&#10;").replace("\t", "&#09;")
    return value


def is_insignificant_whitespace(text: str | None) -> bool:
    """Return True if `text` is None, empty, or contains only whitespace.

    Such text is what pretty-printers insert between elements. It is preserved
    verbatim by default and only discarded when the caller explicitly asks for
    it via ``preserve_whitespace=False``.
    """
    return text is None or text.strip() == ""

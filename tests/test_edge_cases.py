"""XML constructs the Warp fixtures do not contain.

Two of these deserve emphasis:

* namespaces are preserved verbatim. `xml.etree.ElementTree` would rewrite
  `<w:b>` to `{uri}b` and silently discard the `xmlns:w` declaration, which is
  why the parser drives expat directly with namespace processing disabled;
* comments and processing instructions are the only content this package
  drops, and it warns when it does.
"""

from __future__ import annotations

import warnings

import pytest

from warpxmlfile import _xml as xmlfile
from warpxmlfile._xml import XmlLossyContentWarning


def round_trips_exactly(source: str) -> bool:
    return xmlfile.to_string(xmlfile.from_string(source)) == source


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("<a><b>x</b></a>", id="no-declaration"),
        pytest.param(
            '<?xml version="1.0" encoding="utf-8"?>\n<a><b>x</b></a>', id="no-bom"
        ),
        pytest.param("<?xml version='1.0' encoding='UTF-8'?>\n<a />", id="quotes"),
        pytest.param(
            '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<a />',
            id="standalone",
        ),
        pytest.param('<?xml version="1.0"?>\n<a />\n', id="trailing-newline"),
        pytest.param("<a>1 &amp; 2 &lt; 3</a>", id="entities-in-text"),
        pytest.param("<a>a > b</a>", id="literal-gt-in-text"),
        pytest.param("<a>a ]]&gt; b</a>", id="cdata-close-in-text"),
        pytest.param('<a v="x &amp; y" />', id="entities-in-attribute"),
        pytest.param('<a v="l1&#10;l2" />', id="newline-in-attribute"),
        pytest.param('<a v="Å">ångström µm</a>', id="unicode"),
        pytest.param("<a>" + "<b>" * 20 + "x" + "</b>" * 20 + "</a>", id="deep"),
        pytest.param('<a xmlns:w="http://x"><w:b w:c="1" /></a>', id="prefixed-ns"),
        pytest.param('<a xmlns="http://x"><b /></a>', id="default-ns"),
        pytest.param("<a><b /><b /><b /></a>", id="repeated-siblings"),
        pytest.param("<a>text<b />tail</a>", id="mixed-content"),
    ],
)
def test_byte_exact_round_trip(source):
    assert round_trips_exactly(source)


def test_namespace_prefix_and_declaration_are_preserved():
    doc = xmlfile.from_string('<a xmlns:w="http://x"><w:b w:c="1" /></a>')
    assert doc.root.attributes == {"xmlns:w": "http://x"}
    child = doc.root.children[0]
    assert child.tag == "w:b"
    assert child.attributes == {"w:c": "1"}


def test_bom_is_recorded_and_restored():
    source = '﻿<?xml version="1.0" encoding="utf-8"?>\n<a />'
    doc = xmlfile.from_string(source)
    assert doc.byte_order_mark is True
    assert xmlfile.to_string(doc) == source


def test_document_without_bom():
    doc = xmlfile.from_string('<?xml version="1.0"?>\n<a />')
    assert doc.byte_order_mark is False


def test_document_without_declaration():
    doc = xmlfile.from_string("<a />")
    assert doc.declaration is None
    assert xmlfile.to_string(doc) == "<a />"


# -- documented, semantically lossless normalisations -----------------------


def test_empty_element_spelling_is_normalised():
    """`<b></b>` and `<b/>` are the same element; both are written `<b />`."""
    assert xmlfile.to_string(xmlfile.from_string("<a><b></b></a>")) == "<a><b /></a>"
    assert xmlfile.to_string(xmlfile.from_string("<a><b/></a>")) == "<a><b /></a>"


def test_cdata_becomes_escaped_text():
    """CDATA is a way of writing text, not a distinct kind of content."""
    doc = xmlfile.from_string("<a><![CDATA[raw <not> markup]]></a>")
    assert doc.root.text == "raw <not> markup"
    assert xmlfile.to_string(doc) == "<a>raw &lt;not> markup</a>"


def test_only_required_characters_are_escaped():
    """`>` is escaped only where it would close a CDATA section."""
    doc = xmlfile.from_string("<a>a &gt; b</a>")
    assert doc.root.text == "a > b"
    assert xmlfile.to_string(doc) == "<a>a > b</a>"

    doc = xmlfile.from_string("<a>a ]]&gt; b</a>")
    assert doc.root.text == "a ]]> b"
    assert xmlfile.to_string(doc) == "<a>a ]]&gt; b</a>"


def test_crlf_in_content_is_normalised_to_lf():
    """Required of every conforming XML processor, so it is not our choice."""
    doc = xmlfile.from_string('<?xml version="1.0"?>\r\n<a>x\r\ny</a>')
    assert doc.root.text == "x\ny"


# -- the one lossy case ------------------------------------------------------


def test_comments_are_dropped_with_a_warning():
    with pytest.warns(XmlLossyContentWarning, match="comment"):
        doc = xmlfile.from_string("<a><!-- note --><b /></a>")
    assert xmlfile.to_string(doc) == "<a><b /></a>"


def test_processing_instructions_are_dropped_with_a_warning():
    with pytest.warns(XmlLossyContentWarning, match="processing instruction"):
        xmlfile.from_string("<a><?target data?><b /></a>")


def test_no_warning_for_documents_without_comments(xml_path):
    """The real fixtures must not trip the warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", XmlLossyContentWarning)
        xmlfile.read(xml_path)


# -- safety ------------------------------------------------------------------


def test_external_entities_are_refused(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("classified", encoding="utf-8")
    source = (
        '<?xml version="1.0"?>\n'
        f'<!DOCTYPE a [<!ENTITY x SYSTEM "file://{secret}">]>\n'
        "<a>&x;</a>"
    )
    with pytest.raises(xmlfile.XmlParseError):
        xmlfile.from_string(source)

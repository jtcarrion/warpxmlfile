# xmlfile

Read and write XML metadata files in Python.

`xmlfile` is a lightweight [TeamTomo](https://teamtomo.org)-style I/O package
modelled after [`starfile`](https://github.com/teamtomo/starfile). It reads XML
into passive, ordered Python objects and writes those objects back to XML
without changing them.

It is a generic XML reader. It does not interpret cryo-ET metadata, compute
alignments, or convert units. Format-specific interpretation belongs in
explicit adapter functions, added later.

## Installation

```bash
pip install xmlfile
```

## Quickstart

```python
import xmlfile

doc = xmlfile.read("TS_001.xml")
xmlfile.write(doc, "copy.xml")
text = xmlfile.to_string(doc)
```

`copy.xml` is byte-for-byte identical to `TS_001.xml`.

## The data model

Three passive containers, and nothing else:

```python
XmlDocument(root, declaration, byte_order_mark, prologue_tail, epilogue, filename)
XmlElement(tag, attributes, text, children, tail)
XmlDeclaration(version, encoding, standalone, quote)
```

Navigation helpers locate elements; they never interpret them:

```python
doc.root.find("CTF")                    # first child with this tag, or None
doc.root.findall("TiltPS1D")            # all children with this tag, in order
doc.root.get("PixelSize")               # raw attribute value, as a string
for element in doc.root.iter(): ...     # this element and all descendants
```

## What is preserved

Values are always strings. The parser never converts text or attributes to
`int`, `float`, or `bool`, because doing so would discard the exact formatting
of scientific values. Coercion is the job of explicit helper functions.

Preserved on a round trip:

- the XML declaration, including its quote style
- the UTF-8 byte order mark
- root and element attributes, and their order
- child order, and the order of repeated sibling tags
- element text, verbatim, including multi-line blocks and their whitespace
- indentation, whether tabs or spaces, and the absence of a trailing newline
- namespace prefixes and `xmlns` declarations, written exactly as they appear
- unknown elements and attributes, because the model has no notion of "known"

## What is not preserved

`to_string` is byte-exact for every construct except these.

| Input | Output | Why |
| --- | --- | --- |
| `<b></b>` | `<b />` | The same element, written two ways. |
| `<![CDATA[a < b]]>` | `a &lt; b` | CDATA is a way of writing text, not a kind of content. |
| `\r\n` inside content | `\n` | Line-end normalisation is required of every conforming XML processor. |
| `&gt;` in text | `>` | Escaping `>` is only required inside `]]>`, where it is kept. |
| `<!-- comment -->`, `<?pi?>` | dropped | Not represented in the model. |

Only the last of these loses content, and it is never silent: reading such a
document raises an `XmlLossyContentWarning` naming what was discarded.

## Formatting

By default the writer reproduces stored whitespace verbatim, so reading and
writing a file never reformats it. To pretty-print instead, read without
whitespace and pass an indent:

```python
doc = xmlfile.read("TS_001.xml", preserve_whitespace=False)
text = xmlfile.to_string(doc, indent="  ")
```

Pretty-printing leaves significant text alone: the newline-separated per-tilt
blocks that Warp writes into `<Angles>` and `<MoviePath>` are not re-wrapped.

`write` replaces an existing file, as `starfile` and `mdocfile` do, so a
document can be edited and written back over itself:

```python
doc = xmlfile.read("TS_1.xml")
doc.root.attributes["Bfactor"] = "-42"
xmlfile.write(doc, "TS_1.xml")
```

Pass `overwrite=False` to refuse instead.

## Implementation notes

The parser drives `xml.parsers.expat` directly rather than using
`xml.etree.ElementTree`. ElementTree performs namespace processing, which
rewrites `<w:b>` to `{uri}b` and discards the `xmlns:w` declaration outright.
Silently dropping an attribute is precisely what this package exists to
prevent, so expat is used with namespace processing switched off.

External entity references are refused, so a document cannot cause the parser
to read files off disk.

## Development

The tooling follows the other TeamTomo I/O packages (`alnfile`): [uv](https://docs.astral.sh/uv/)
for environments, `ruff` for linting and formatting, `mypy` in strict mode, `pytest`
with warnings turned into errors, and `pre-commit` to run all of it before a commit.

```bash
uv sync --group dev                       # create .venv with the dev tools
uv run pytest
uv run pre-commit run --all-files         # ruff, ruff-format, mypy, typos, validate-pyproject
```

Without uv: `pip install -e . --group dev` (pip >= 25.1) then run `pytest`,
`ruff check .`, `ruff format --check .` and `mypy` directly.

### Test data

`tests/data/TS_1.xml` is a real Warp tilt-series file, the most structurally
complete one available: 112 child elements, 41 tilts, and dense movement and
volume-warp grids totalling 5373 nodes. The absolute path in `DataDirectory`
has been replaced with a placeholder; the file is otherwise unmodified.

One file cannot represent the variation between Warp workflows, which differ
in root attribute count, tilt count and grid density. Point the suite at a
directory of your own files to check every one of them for a byte-exact round
trip, without that data entering the repository:

```bash
pytest --xml-corpus /path/to/warp_tiltseries
```

## License

BSD 3-Clause.

# xmlfile

Read and write XML metadata files in Python.

`xmlfile` is a lightweight [TeamTomo](https://teamtomo.org)-style I/O package
modelled after [`starfile`](https://github.com/teamtomo/starfile) and [`alnfile`](https://github.com/teamtomo/alnfile). 

It is a generic XML reader. It does not interpret cryo-ET metadata, compute
alignments, or convert units. 

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


Navigation helpers locate elements; they never interpret them:

```python
doc.root.find("CTF")                    # first child with this tag, or None
doc.root.findall("TiltPS1D")            # all children with this tag, in order
doc.root.get("PixelSize")               # raw attribute value, as a string
for element in doc.root.iter(): ...     # this element and all descendants
```

`write` replaces an existing file, as `starfile` and `mdocfile` do, so a
document can be edited and written back over itself:

```python
doc = xmlfile.read("TS_1.xml")
doc.root.attributes["Bfactor"] = "-42"
xmlfile.write(doc, "TS_1.xml")
```

Pass `overwrite=False` to refuse instead.

## Helpers

The core never converts values. These functions do, for the patterns that
recur in cryo-ET metadata XML (numpy is the only dependency):

```python
angles = xmlfile.text_to_list(root.find("Angles"), float)     # whitespace-separated text
used   = xmlfile.text_to_list(root.find("UseTilt"), bool)     # "True"/"False" only
params = xmlfile.params_to_dict(root.find("CTF"))             # {Name: Value} of <Param/> children
grid   = xmlfile.grid_to_array(root.find("GridMovementX"))    # float32, shape (Depth, Height, Width)
series = xmlfile.parse_pair_series(root.find("TiltPS1D"))     # (n, 2) from "x|y;x|y;..."
```

A 4-D grid (an element with a `Duration` attribute) gives shape
`(Duration, Depth, Height, Width)`; `grid.ravel()` lists the nodes with `X`
varying fastest, the order in the file. `grid_margins` returns the
`MarginX/Y/Z[/W]` attributes.


## Test data

`tests/data/TS_1.xml` is a real WarpTools tilt-series file: 112 child elements, 41 tilts, and dense movement and
volume-warp grids totalling 5373 nodes. 

Point the suite at a directory of your own files to check every one of them for a byte-exact round
trip, without that data entering the repository:

```bash
pytest --xml-corpus /path/to/warp_tiltseries
```

## License

BSD 3-Clause.

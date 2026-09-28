# warpxmlfile

Read and write Warp / M tilt-series XML files in Python.

`warpxmlfile` is a lightweight [TeamTomo](https://teamtomo.org)-style I/O package
modelled after [`starfile`](https://github.com/teamtomo/starfile) and [`alnfile`](https://github.com/teamtomo/alnfile).

It deserialises what the file says and serialises it back. It does not interpret
the data: no unit or sign conventions, no coordinate frames, no evaluation of the
deformation grids, no tilt-series geometry. Those belong to the packages that
consume it (e.g. `torch-tilt-series`).

## Installation

```bash
pip install warpxmlfile
```

## Quickstart

```python
import warpxmlfile

ts = warpxmlfile.read("TS_001.xml")          # -> WarpTiltSeries

ts.angles                                    # per-tilt float array, from <Angles>
ts.axis_offset_x, ts.axis_offset_y           # Angstroms, as written in <AxisOffsetX/Y>
ts.use_tilt                                  # bool array, from <UseTilt>
ts.ctf["PixelSize"]                          # '1.7005' - <Param> values are kept as text
ts.grids["GridMovementX"].values             # float32, shape (Depth, Height, Width)
ts.attributes["ImageDimensionsAngstrom"]     # root attributes, verbatim

warpxmlfile.write(ts, "copy.xml")            # byte-for-byte identical to TS_001.xml
```

The same operations exist on the model, as in `alnfile`:
`WarpTiltSeries.from_file(path)`, `WarpTiltSeries.from_string(text)`,
`ts.to_string()`, `ts.to_file(path)`.

## Editing

The parsed document is kept with the model, so writing changes only the
elements whose values you edited and leaves every other byte alone:

```python
ts = warpxmlfile.read("TS_001.xml")
ts.axis_offset_x += 30.0                                   # shift every tilt by 30 A
ts.grids["GridMovementX"] = warpxmlfile.Grid(
    values=numpy.zeros((ts.n_tilts, 3, 3), numpy.float32), margins=(0.0, 0.0, 0.0)
)
warpxmlfile.write(ts, "TS_001.xml")                        # overwrite=False to refuse
```

Numbers are written the way Warp writes them (the shortest text that round-trips
the value as a 32-bit float), so an edited file differs from the original only on
the edited lines. A model built from scratch, `WarpTiltSeries(angles=..., ...)`,
is written in Warp's own layout.

## The model

| field | from | type |
| --- | --- | --- |
| `attributes` | root attributes | `dict[str, str]`, verbatim |
| `angles`, `axis_angle`, `axis_offset_x`, `axis_offset_y` | per-tilt elements | float arrays, length `n_tilts` |
| `use_tilt` | `UseTilt` | bool array |
| `dose`, `fov_fraction`, `movie_path` | per-tilt elements | as found (`None`/empty if absent); Warp may write a single value for a series |
| `ctf`, `options_ctf` | `Param` blocks | `dict[str, str]` (`None` if absent) |
| `grids` | every `Grid*` element | `dict[str, Grid]`; `Grid.values` float32 `(Depth, Height, Width)` or `(Duration, Depth, Height, Width)`, `Grid.margins` |
| `tilt_ps1d`, `tilt_simulated_scale` | repeated elements | `list` of `(n, 2)` arrays |
| `extra` | anything else | tag names, preserved on write |

`image_dimensions_angstrom` and `volume_dimensions_angstrom` are typed views of
the corresponding root attributes. Reading validates what the file must satisfy
(per-tilt lengths of the required elements, complete grids, no duplicate
`Param` names) and raises `ValueError` otherwise; it never silently repairs.

## What is and is not preserved

Unedited content round-trips byte for byte: the XML declaration, the byte order
mark, indentation with tabs, attribute and element order, numbers exactly as
written, elements the model does not know (they are listed in `extra`).
Two cosmetic normalisations apply to files written by other tools: `<b/>` is
written as `<b />` (Warp's spelling) and `\r\n` becomes `\n`. Comments and
processing instructions are dropped with a warning.

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

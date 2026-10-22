# warpxmlfile

Read and write Warp / M tilt-series XML files in Python, in the spirit of
[`starfile`](https://github.com/teamtomo/starfile) and [`alnfile`](https://github.com/teamtomo/alnfile).
The file is deserialised as written and serialised back byte for byte; nothing is interpreted
(no units, signs, frames or grid evaluation). Geometry belongs to the consumers, e.g.
`torch-tilt-series`.

## Installation

```bash
pip install warpxmlfile
```

## Reading

```python
import warpxmlfile

ts = warpxmlfile.read("TS_001.xml")          # -> WarpTiltSeries (pydantic model)

ts.angles                                    # per-tilt float array, from <Angles>
ts.axis_offset_x, ts.axis_offset_y           # Angstroms, as written
ts.use_tilt                                  # bool array
ts.ctf["PixelSize"]                          # '1.7005' - <Param> values are kept as text
ts.grids["GridMovementX"].values             # float32, shape (Depth, Height, Width)
ts.attributes["ImageDimensionsAngstrom"]     # root attributes, verbatim
```

## Editing and writing

Writing changes only the values you edited and leaves every other byte alone:

```python
ts = warpxmlfile.read("TS_001.xml")
ts.axis_offset_x += 30.0                     # shift every tilt by 30 A
warpxmlfile.write(ts, "TS_001_shifted.xml")
```

Numbers are written as Warp writes them (shortest text that round-trips the 32-bit float).
The same operations exist on the model: `WarpTiltSeries.from_file`, `.from_string`,
`.to_string`, `.to_file`. Reading validates the file (per-tilt lengths, complete grids, unique
`Param` names) and raises `ValueError` otherwise. Elements the model does not know are kept in
`ts.extra` and preserved on write.

## License

BSD 3-Clause.

"""The public model: read -> WarpTiltSeries -> write, on the fixture."""

from __future__ import annotations

import numpy as np
import pytest
from conftest import FIXTURES

import warpxmlfile
from warpxmlfile import Grid, WarpTiltSeries


@pytest.fixture
def ts(xml_path) -> WarpTiltSeries:
    return warpxmlfile.read(xml_path)


def _changed_lines(a: str, b: str) -> list[int]:
    la, lb = a.splitlines(), b.splitlines()
    assert len(la) == len(lb)
    return [i for i, (x, y) in enumerate(zip(la, lb, strict=True)) if x != y]


def test_read_fields(ts, fixture):
    assert ts.n_tilts == fixture.tilts
    for name in (
        "angles",
        "dose",
        "axis_angle",
        "axis_offset_x",
        "axis_offset_y",
        "fov_fraction",
    ):
        assert getattr(ts, name).shape == (fixture.tilts,)
    assert ts.use_tilt.dtype == bool and ts.use_tilt.all()
    assert len(ts.movie_path) == fixture.tilts and ts.movie_path[0].endswith(".tif")
    assert ts.angles[0] == -40.01
    assert len(ts.attributes) == fixture.root_attributes
    assert ts.image_dimensions_angstrom is None  # this fixture predates the attribute
    ts.attributes["ImageDimensionsAngstrom"] = "100, 200"
    assert ts.image_dimensions_angstrom == (100.0, 200.0)
    assert len(ts.ctf) == fixture.ctf_params and ts.ctf["PixelSize"] == "0.7894"
    assert len(ts.options_ctf) == fixture.options_ctf_params
    assert ts.grids["GridMovementX"].values.shape == (41, 4, 6)
    assert ts.grids["GridMovementX"].values.dtype == np.float32
    assert ts.grids["GridMovementX"].margins == (0.0, 0.0, 0.0)
    assert ts.grids["GridVolumeWarpX"].values.shape == (41, 1, 6, 4)
    assert len(ts.tilt_ps1d) == fixture.tilts and ts.tilt_ps1d[0].shape == (256, 2)
    assert len(ts.tilt_simulated_scale) == fixture.tilts
    assert ts.extra == ["PS1D", "SimulatedScale"]  # untyped, preserved on write


def test_unchanged_model_is_byte_exact(ts, xml_path):
    assert warpxmlfile.to_string(ts) == xml_path.read_text(encoding="utf-8")


def test_write_round_trip(ts, tmp_path):
    out = tmp_path / "copy.xml"
    warpxmlfile.write(ts, out)
    again = warpxmlfile.read(out)
    assert np.array_equal(again.angles, ts.angles)
    assert again.ctf == ts.ctf
    assert np.array_equal(
        again.grids["GridMovementY"].values, ts.grids["GridMovementY"].values
    )
    with pytest.raises(FileExistsError):
        warpxmlfile.write(ts, out, overwrite=False)


def test_edit_offsets_changes_only_those_lines(ts, xml_path):
    original = xml_path.read_text(encoding="utf-8")
    ts.axis_offset_x = ts.axis_offset_x + 30.0
    edited = warpxmlfile.to_string(ts)
    changed = _changed_lines(original, edited)
    assert len(changed) == ts.n_tilts
    reread = warpxmlfile.from_string(edited)
    assert np.allclose(reread.axis_offset_x, ts.axis_offset_x)
    assert np.array_equal(reread.axis_offset_y, ts.axis_offset_y)


def test_in_place_edit_is_detected(ts, xml_path):
    ts.angles[0] += 1.0  # mutate the array, not the attribute
    edited = warpxmlfile.to_string(ts)
    assert len(_changed_lines(xml_path.read_text(encoding="utf-8"), edited)) == 1


def test_edit_grid_changes_only_that_element(ts, xml_path):
    original = xml_path.read_text(encoding="utf-8")
    g = ts.grids["GridMovementX"]
    g.values = g.values + np.float32(1.5)
    edited = warpxmlfile.to_string(ts)
    changed = _changed_lines(original, edited)
    assert len(changed) == g.values.size
    assert all("<Node " in edited.splitlines()[i] for i in changed)
    assert np.array_equal(
        warpxmlfile.from_string(edited).grids["GridMovementX"].values, g.values
    )


def test_replace_grid_with_new_shape(ts, xml_path):
    ts.grids["GridMovementX"] = Grid(
        values=np.zeros((ts.n_tilts, 3, 3), dtype=np.float32), margins=(0.0, 0.0, 0.0)
    )
    reread = warpxmlfile.from_string(warpxmlfile.to_string(ts))
    assert reread.grids["GridMovementX"].values.shape == (ts.n_tilts, 3, 3)
    assert reread.grids["GridMovementY"].values.shape == (41, 4, 6)  # untouched


def test_edit_attributes_and_params(ts):
    ts.attributes["Weight"] = "0.5"
    ts.ctf["PixelSize"] = "1.0000"
    reread = warpxmlfile.from_string(warpxmlfile.to_string(ts))
    assert reread.attributes["Weight"] == "0.5" and reread.ctf["PixelSize"] == "1.0000"
    assert len(reread.ctf) == len(ts.ctf)


def test_edit_pair_series(ts):
    ts.tilt_ps1d[0] = ts.tilt_ps1d[0] * 2
    reread = warpxmlfile.from_string(warpxmlfile.to_string(ts))
    assert np.allclose(reread.tilt_ps1d[0], ts.tilt_ps1d[0])
    ts.tilt_ps1d.pop()
    with pytest.raises(ValueError, match="number of <TiltPS1D>"):
        warpxmlfile.to_string(ts)


def test_from_scratch_serialises_in_warp_layout():
    n = 3
    ts = WarpTiltSeries(
        attributes={"ImageDimensionsAngstrom": "4000, 4000"},
        angles=np.array([-30.0, 0.0, 30.0]),
        use_tilt=np.array([True, True, True]),
        axis_angle=np.full(n, 85.0),
        axis_offset_x=np.zeros(n),
        axis_offset_y=np.zeros(n),
        ctf={"PixelSize": "2.5"},
        grids={
            "GridMovementX": Grid(
                values=np.zeros((n, 1, 1), np.float32), margins=(0.0, 0.0, 0.0)
            )
        },
    )
    text = warpxmlfile.to_string(ts)
    head = (
        '\ufeff<?xml version="1.0" encoding="utf-8"?>\n'
        '<TiltSeries ImageDimensionsAngstrom="4000, 4000">\n'
        "\t<Angles>-30\n0\n30</Angles>\n\t"
    )
    assert text.startswith(head)
    reread = warpxmlfile.from_string(text)
    assert np.array_equal(reread.angles, ts.angles) and reread.ctf == ts.ctf
    assert reread.grids["GridMovementX"].values.shape == (n, 1, 1)
    assert reread.image_dimensions_angstrom == (4000.0, 4000.0)


def test_not_a_warp_file():
    with pytest.raises(ValueError, match="no <Angles>"):
        warpxmlfile.from_string("<TiltSeries />")
    with pytest.raises(ValueError, match="expected 2"):
        warpxmlfile.from_string(
            "<TiltSeries><Angles>0\n1</Angles><UseTilt>True</UseTilt><AxisAngle>0\n0</AxisAngle>"
            "<AxisOffsetX>0\n0</AxisOffsetX><AxisOffsetY>0\n0</AxisOffsetY></TiltSeries>"
        )


def test_fixture_list_is_the_only_one():
    assert len(FIXTURES) == 1


def test_model_classmethods_match_module_functions(xml_path, tmp_path):
    ts = WarpTiltSeries.from_file(xml_path)
    assert ts.to_string() == warpxmlfile.to_string(warpxmlfile.read(xml_path))
    assert np.array_equal(WarpTiltSeries.from_string(ts.to_string()).angles, ts.angles)
    ts.to_file(tmp_path / "copy.xml")
    assert (tmp_path / "copy.xml").read_text(encoding="utf-8") == ts.to_string()
    with pytest.raises(FileExistsError):
        ts.to_file(tmp_path / "copy.xml", overwrite=False)

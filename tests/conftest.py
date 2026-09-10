"""Shared fixtures.

The repository ships a single Warp tilt-series XML file. It is the most
structurally complete one available: 112 child elements, 41 tilts, and dense
movement and volume-warp grids (984 nodes each, 5373 grid nodes in total).

One committed file cannot cover the variation between Warp workflows, so the
suite also accepts a corpus of local files that are too numerous, too large,
or too unpublished to commit:

    pytest --xml-corpus /path/to/warp_tiltseries

Every ``.xml`` file found there is checked for a byte-exact round trip. This
is how the parser is validated against real variation without that data
entering the repository.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


class Fixture:
    """Expected structure of a test file, measured from the file itself."""

    def __init__(
        self,
        name: str,
        root_attributes: int,
        children: int,
        tilts: int,
        ctf_params: int,
        options_ctf_params: int,
        grid_movement_x_nodes: int,
        grid_volume_warp_x_nodes: int,
    ) -> None:
        self.name = name
        self.path = DATA_DIR / name
        self.root_attributes = root_attributes
        self.children = children
        self.tilts = tilts
        self.ctf_params = ctf_params
        self.options_ctf_params = options_ctf_params
        self.grid_movement_x_nodes = grid_movement_x_nodes
        self.grid_volume_warp_x_nodes = grid_volume_warp_x_nodes

    def __repr__(self) -> str:
        return self.name


FIXTURES = [
    Fixture(
        "TS_1.xml",
        root_attributes=9,
        children=112,
        tilts=41,
        ctf_params=21,
        options_ctf_params=24,
        grid_movement_x_nodes=984,
        grid_volume_warp_x_nodes=984,
    ),
]

# Fields written as newline-separated per-tilt lists in Warp tilt-series XML.
PER_TILT_TAGS = [
    "Angles",
    "Dose",
    "UseTilt",
    "AxisAngle",
    "AxisOffsetX",
    "AxisOffsetY",
    "MoviePath",
    "FOVFraction",
]


def pytest_addoption(parser):
    parser.addoption(
        "--xml-corpus",
        action="store",
        default=None,
        metavar="DIR",
        help="directory of XML files to check for byte-exact round trips",
    )


@pytest.fixture(scope="session")
def corpus_paths(request) -> list[Path]:
    directory = request.config.getoption("--xml-corpus")
    if directory is None:
        pytest.skip("no --xml-corpus directory given")
    path = Path(directory)
    if not path.is_dir():
        pytest.fail(f"--xml-corpus is not a directory: {path}")
    paths = sorted(path.glob("*.xml"))
    if not paths:
        pytest.fail(f"no .xml files in {path}")
    return paths


@pytest.fixture(params=FIXTURES, ids=lambda f: f.name)
def fixture(request) -> Fixture:
    return request.param


@pytest.fixture
def xml_path(fixture: Fixture) -> Path:
    return fixture.path


def count_lines(text: str | None) -> int:
    """Number of non-empty lines in a newline-separated text field."""
    if text is None:
        return 0
    return len([line for line in text.split("\n") if line.strip()])

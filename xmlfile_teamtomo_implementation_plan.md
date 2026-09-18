# xmlfile TeamTomo Implementation Plan

Prepared for developing a small TeamTomo-style XML I/O package modeled after `starfile`.

## 0. Current status and handoff (updated 2026-09-17, evening)

> Read this section first. It is self-contained and supersedes anything below
> that conflicts with it. Sections 1–20 are the original plan (2026-09-09),
> kept for its reasoning; parts that changed are marked **Superseded** inline.

### 0.1 Where everything is

| Item | Location / state |
| --- | --- |
| Repository (HPC) | `/orcd/data/mbathe/001/jcarrion/software/xmlfile` |
| Repository (laptop) | `~/Desktop/particle_picker/code/xmlfile`, clone of GitHub `main`; editable-installed into the `particle_picker` conda env (Python 3.10.14, `pip install -e . --ignore-requires-python`) — 77 passed, 1 skipped. |
| Branch `main` | One commit, `0047f1e` "Add generic ordered XML read/write round-trip support". Clean tree. This is the branch that will eventually go to TeamTomo. |
| Branch `notes` | Orphan branch (no shared history with `main`) holding only this plan (`6a71b8e`). Keeps planning material out of `main` so it cannot be merged in by accident. A working copy of the plan also sits (gitignored) at the root of the `particle_picker` repo; the `notes` branch is canonical — push the same file to both. |
| This plan on `main` | Gitignored on purpose. |
| GitHub | **Pushed.** Private repo `jtcarrion/xmlfile`, `origin/main` = `0047f1e`, `origin/notes` = `6a71b8e`. |
| PyPI | `xmlfile` is **not taken** (checked 2026-09-17; `warpxml`, `warpfile` also free). |
| TeamTomo | Nothing submitted. No Zulip post yet. `teamtomo/xmlfile` does not exist. |
| Consumer | `particle_picker` (branch `feature/local-alignment-ba`) plans to use xmlfile for its G3 step: write a per-tilt 3×3 local-alignment grid into an existing Warp XML in place (`local_alignment_BA.md` §7/§8). No code there calls xmlfile yet; Warp XML is currently read through the vendored `warpylib` (lxml). |

### 0.2 Picking this up on a new machine

```bash
git clone git@github.com:jtcarrion/xmlfile.git
cd xmlfile
git show origin/notes:xmlfile_teamtomo_implementation_plan.md > xmlfile_teamtomo_implementation_plan.md

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install pytest                 # enough: pyproject sets pythonpath = ["src"]
pytest                             # expect: 77 passed, 1 skipped
```

`pip install -e .` **is verified** on the laptop (Python 3.10, needs
`--ignore-requires-python` until the floor is lowered in step 2 below; hatchling
and hatch-vcs come from PyPI, which the laptop can reach). The skipped test is the
corpus test, which needs local data (see 0.10).

### 0.3 Milestone status

| Milestone | Status |
| --- | --- |
| M0 bootstrap | **Done** (PR #1, on `main`): alnfile-aligned pyproject (py3.10 floor, dependency groups, ruff numpy docstrings, mypy strict, pytest warnings-as-errors), pre-commit, CI matrix green (3.10–3.13 × 3 OS; `core-metadata-version = "2.4"` pinned because build-and-inspect@v2's twine rejects hatchling ≥ 1.32's 2.5). |
| M1 ordered XML core | **Done.** 77 tests pass; byte-exact round trip on the fixture and on 201 local Warp files. |
| M2 helpers | **Done** (PR #2, on `main`): `text_to_list`/`list_to_text`, `params_to_pairs`/`params_to_dict`, `grid_to_array`/`grid_margins`/`array_to_grid`, `parse_pair_series`/`pair_series_to_text`; 100 tests; numpy the only dependency. |
| M3 Warp adapter in xmlfile | **Dropped** for v0.0.1 (decision 6). |
| M4 torch-tilt-series loader | **Mapping fully validated (0.11, phases A–D); loader not yet written** — option 3 in 0.11.3. Branch `feat/warp-xml-loader` exists in `~/Software/teamtomo` (clean, at `origin/main` `2d9f20c`). |

### 0.4 What is built on `main`

```text
.gitattributes          tests/data/*.xml -text (no CRLF translation, protects byte-exactness on Windows CI)
.gitignore
LICENSE                 BSD 3-Clause
README.md
pyproject.toml          hatchling + hatch-vcs; ruff; mypy strict; pytest pythonpath=src; requires-python >=3.11; no runtime deps
src/xmlfile/
  __init__.py           exports read, write, to_string, from_string, XmlDocument, XmlElement,
                        XmlDeclaration, XmlParseError, XmlLossyContentWarning, __version__
  functions.py          thin public wrappers
  models.py             XmlDeclaration, XmlElement (find/findall/get/iter), XmlDocument
  parser.py             XmlParser on xml.parsers.expat (namespace processing off)
  writer.py             XmlWriter: verbatim (default) or pretty (indent=...)
  typing.py, utils.py, py.typed
tests/
  conftest.py           Fixture metadata; --xml-corpus option
  data/TS_1.xml         the single committed fixture
  test_read.py  test_round_trip.py  test_write.py  test_models.py
  test_errors.py  test_edge_cases.py  test_corpus.py
```

Behaviour:

- `read(path, preserve_whitespace=True)` → `XmlDocument`. Values are always strings; nothing is coerced, reordered or dropped.
- `XmlDocument` fields: `root`, `declaration`, `byte_order_mark`, `prologue_tail`, `epilogue`, `filename` (`filename` is excluded from equality).
- `to_string(doc)` reproduces the source **byte for byte** by default (BOM, tabs, no trailing newline). `to_string(doc, indent="  ")` pretty-prints; best used with `read(..., preserve_whitespace=False)`.
- `write(doc, path)` **overwrites by default**; `overwrite=False` raises `FileExistsError`.
- Namespaces: prefixes and `xmlns` declarations are kept verbatim.
- External entity references are refused (`XmlParseError`).
- Comments and processing instructions are dropped **with an `XmlLossyContentWarning`**.

Byte-exact exceptions (all semantically lossless except the last):

| Input | Output |
| --- | --- |
| `<b></b>` or `<b/>` | `<b />` |
| `<![CDATA[a < b]]>` | `a &lt; b` |
| `\r\n` in content | `\n` (required by the XML spec) |
| `&gt;` in text | `>` (`>` is only escaped inside `]]>`) |
| comments, processing instructions | dropped, with a warning |

Fixture: `tests/data/TS_1.xml` comes from EMPIAR-10491 (a public deposition), from
`processing/EMPIAR-10491-5TS/warp_tiltseries/TS_1.xml`. 9 root attributes,
112 children, 41 tilts, CTF 21 params, OptionsCTF 24 params, GridMovementX
and GridVolumeWarpX 984 nodes each (5373 grid nodes total). `DataDirectory` was replaced with
`/path/to/tomostar`; nothing else changed.

History: the three original fixtures (including unpublished bmp6 data) were
committed early, then removed. History was then squashed to one commit and
garbage-collected, so they are **not** in `main`'s history.

### 0.5 Decisions made (answers to section 19)

1. **Name:** keep `xmlfile`. PyPI name is free (checked 2026-09-17).
2. **Fixtures:** commit one file only (`TS_1.xml`, public EMPIAR provenance, most complete available). Other XML stays local and is validated with `pytest --xml-corpus DIR`.
3. **Parser:** standard library yes, `ElementTree` no. ElementTree rewrites `<w:b>` to `{uri}b` and silently deletes the `xmlns:w` attribute, so the parser drives `expat` directly. No lxml.
4. **Fidelity:** byte-exact by default; pretty-printing opt-in. Only comments/PIs lose content. Closing the cosmetic gaps would need a custom lexer and is not planned; comment/PI node types could be added if a real file needs them. Property-based tests (`hypothesis`) are an option for stronger guarantees.
5. **pandas:** acceptable as a dependency (TeamTomo I/O packages such as alnfile already depend on it). **Revised 2026-09-17:** v0.0.1 helpers return NumPy arrays (numpy becomes the only runtime dependency); pandas stays out until a DataFrame-shaped helper is actually needed.
6. **Scope of v0.0.1:** a robust reader/writer plus helper functions. No Warp-specific adapter in xmlfile. Downstream goal: a loader in torch-tilt-series that uses the XML data.
7. **Overwrite:** `write` overwrites by default, like starfile and mdocfile. This supports editing ("perturbing") alignments and rerunning torch-tilt-series.
8. **Python floor: 3.10** (2026-09-17). alnfile's floor; the code uses nothing from 3.11; the main consumer env is 3.10.
9. **Template (open decision A): hand-align** `pyproject.toml` / pre-commit / CI to alnfile (`b582488`) rather than regenerate with copier. Test data stays in `tests/data/` (open decision D).
10. **Helper design (open decision C):** generic, Warp-agnostic names — `text_to_list`, `params_to_dict` / `params_to_pairs`, `grid_to_array` / `array_to_grid` (a `NodeGrid(values, margins)` dataclass; `values` in zyx / C order `(Depth, Height, Width)` or `(Duration, Depth, Height, Width)`, identical to warpylib's flat node order `((w·D + z)·H + y)·W + x`), `parse_pair_series`. Strict validation (node count, missing/duplicate nodes raise). `array_to_grid` takes a `template` element so an in-place replacement keeps the file's indentation. Warp-specific interpretation (`from_warp_xml`, signs, frames) stays downstream in torch-tilt-series (decision 6).
11. **Branching:** one branch per step (`chore/teamtomo-conventions`, `feat/helpers`) merged into `main`; commits carry the `Co-Authored-By: Claude …` trailer.

### 0.6 Research findings (2026-09-10)

**Route into TeamTomo.** TeamTomo is now a monorepo (`teamtomo/teamtomo`,
`packages/{primitives,algorithms,utils,skel}`). torch-tilt-series is in
`packages/primitives/`, torch-tiltxcorr in `packages/algorithms/`. But
`CONTRIBUTING.md` says: *"if this is an I/O package, please reach out on Zulip
for creating a new repo under the organization."* So xmlfile does **not** go in
the monorepo: post on Zulip (imagesc.zulipchat.com, channel TeamTomo) and
maintainers create `teamtomo/xmlfile`.

**Template to match: `teamtomo/alnfile`**, a standalone I/O repo that torch-tilt-series
consumes through `torch-tilt-series[io]`. It has:

- `.copier-answers.yml` from `gh:pydev-guide/pyrepo-copier`, mode `tooling`
- `test_data/` at the repo root (we use `tests/data/`)
- `mkdocs.yml` and `docs/index.md` (MkDocs Material)
- `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, dependabot, issue templates
- CI: uv; Python 3.10–3.13 on ubuntu, macos and windows; a check-manifest job
- `requires-python = ">=3.10"`; depends on pandas and pydantic

**Monorepo `packages/skel/pyproject.toml` conventions** we do not yet follow:
`[dependency-groups]` (PEP 735) for test/dev; ruff selects `E W F D D417 I UP C4 B A001 RUF TCH TID`
with pydocstyle numpy convention; mypy `strict = true` with
`disallow_any_generics = false`, `disallow_subclassing_any = false`;
pytest `filterwarnings = ["error"]`; coverage and check-manifest config.

**What torch-tilt-series needs (re-checked 2026-09-17 against monorepo
`a15f012` = PyPI 0.6.0, released 2026-09-11).** `torch_tilt_series/io.py` has
`from_aretomo_output(aln_path, pixel_spacing, image_path=None, device="cpu")`
and `from_etomo_directory(etomo_dir, pixel_spacing, device)` (both import their
I/O package lazily; `io` extra = `alnfile, etomofiles, mrcfile`), plus
`load_tilt_series_images`. A `from_warp_xml(xml_path, image_path=None, device)`
built on xmlfile would follow the same pattern. `TiltSeries.__init__` now also
takes `x_tilts`, `sample2levelled`, `levelled2tomo`, **`local_shifts`** (sample
space, 3D) and **`local_shifts_2d`** (`Callable[(n_points, n_tilts, 2|4) Å,
detector-centred] -> same`, applied per tilt *after* projection) — i.e. the hook
for Warp's `GridMovementX/Y` already exists. All coordinates are zyx/yx, Å,
centre-origin. Nothing in the monorepo reads XML or Warp files; pre-commit
(ruff, mypy, typos, validate-pyproject) is enforced in CI since 2026-09-11.
Mapping from `TiltSeries.__init__` to Warp XML:

| TiltSeries parameter | Warp XML source | Confidence |
| --- | --- | --- |
| `tilt_angles` | `<Angles>` | direct |
| `tilt_axis_angle` | `<AxisAngle>` | direct |
| `sample_translations` (Å, `(y, x)` per tilt) | `<AxisOffsetY>`, `<AxisOffsetX>` | **units and sign unverified** |
| `pixel_spacing` | `CTF/Param[@Name="PixelSize"]` | direct |
| `image_indices` | `<UseTilt>` | direct |
| `image_path` | `<MoviePath>` (relative paths) | direct |
| `x_tilts`, `sample2levelled` | `PlaneNormal`, `LevelAngleX/Y` (some workflows) | needs work |
| `local_shifts_2d` (`Callable[[Tensor], Tensor]`) | `GridMovementX/Y` (per tilt; Warp samples at the *pre-movement* position, normalised by `ImageDimensionsAngstrom`, t = tilt/(T−1) over **all** tilts, and **subtracts**) | closure over the grids + image dims + pixel size; must map used tilts back to Warp rows when `UseTilt` has `False` entries |
| `local_shifts` (3D, sample space) | `GridVolumeWarpX/Y/Z` (4D: x, y, z, dose/time) | later |

The commit the user linked, `2c81e6b` (PR #126, Marten Chaillet, 2026-09-08),
moved tilt-image loading and preprocessing from torch-reconstruct-tomogram into
torch-tilt-series. That module is actively changing, so coordinate before
building against it. The commit uses the same `Co-Authored-By: Claude …` /
`Claude-Session:` trailer style as our commit.

### 0.6.1 Empirical checks on Warp files (2026-09-17)

On an M-refined bmp6 file (`TS_042.xml`, 36 tilts, `GridMovementX/Y` 6×4×36 =
864 nodes, `GridVolumeWarp` 4D, 485,950 bytes): byte-exact round trip in
0.02 s; editing one `Node Value` changes exactly one line; replacing
`GridMovementX` with a hand-built 3×3×36 `XmlElement` serialises correctly with
the file's tab indentation carried by `tail`. What had to be done by hand —
node ordering, per-node `tail` whitespace, float formatting (warpylib writes
`.9g`; Warp writes C# shortest-round-trip, e.g. `-4.46617`) — is exactly the
M2 helper scope. The EMPIAR `00254.xml` (etomo import, no M) has only 1×1×1
grids; the TS_1 fixture has `GridVolumeWarp` with `Depth="1" Duration="41"`,
bmp6 has `Depth="4" Duration="10"` — helpers must handle both 3D and 4D.

### 0.7 Known issues and suspicions (unverified)

- **mypy strict probably fails**: untyped `**kwargs` in `functions.py` (`to_string`, `write`); `_refuse_external_entity` in `parser.py` is annotated `-> bool` but always raises.
- **ruff `D` rules** (if adopted from the TeamTomo template) will flag docstrings that are not numpy style.
- `pyproject.toml` uses `[project.optional-dependencies]` for test/dev; TeamTomo uses `[dependency-groups]`.
- hatch-vcs without a git tag gives a version like `0.1.dev1+g0047f1e`.
- The corpus directories are HPC-only.

### 0.8 Open decisions

- ~~A. Template~~ → decided: hand-align (0.5 #9).
- ~~B. Python floor~~ → decided: 3.10 (0.5 #8).
- ~~C. Helper design~~ → decided: NumPy arrays, generic names (0.5 #10).
- ~~D. Test data location~~ → decided: keep `tests/data/` (0.5 #9).
- **E. Release/version:** when to tag `v0.0.1` (after steps 2–4 below).
- **F. `AxisOffsetX/Y` units and sign** (and the y/x order, the sign of the in-plane rotation, the grid sign/frame, and all-vs-used tilts): to be settled **numerically** (step 4 below) against warpylib's `get_position_in_all_tilts`, not by documentation.

### 0.9 Next steps, in order

1. ~~Create the GitHub repo and push~~ — done (0.1). This plan updated 2026-09-17 (step 1 of the 2026-09-17 agreement).
2. ~~Conventions~~ — done, PR #1 merged (`988a3c7`). Was: `requires-python >=3.10`; `[dependency-groups]`; ruff/mypy/pytest (`filterwarnings = ["error"]`)/coverage/check-manifest/typos blocks from alnfile; `.pre-commit-config.yaml`; alnfile's `.github/workflows/ci.yml` (incl. the trusted-publishing job, inert until a `v*` tag); numpy-style docstrings; explicit typed keyword parameters for `to_string`/`write` (same keyword names); tests using `pytest.warns` for the lossy-content warning. Run ruff, ruff-format and mypy in a `uv sync --group dev` venv until green.
3. ~~M2 helpers~~ — done, PR #2 merged. Was: (branch `feat/helpers`, `src/xmlfile/helpers.py`), design per 0.5 #10; tests on `TS_1.xml` (984-node 3D grids, 4D grids, 41 tilts, CTF/OptionsCTF params, `TiltPS1D`), array→grid→array identity, in-place replacement round trip, error cases; `--xml-corpus` on the bmp6 directory locally. This is the same implementation that `particle_picker` G3 will call.
4. ~~Numerical proof of the Warp ↔ torch-tilt-series mapping~~ — **done, phases A–D**; see **0.11** (revised 2026-09-17: lives in `~/Software/xmlfile-validation/`, not in `particle_picker`, against the monorepo clone `~/Software/teamtomo`). Original wording: (i) xmlfile arrays == warpylib `CubicGrid.values` on `TS_042.xml`; (ii) hand-built `TiltSeries(..., local_shifts_2d=closure)` vs warpylib `get_position_in_all_tilts` on random points, enumerating the sign / order / frame hypotheses, target < 0.05 px; (iii) the G3 path: `array_to_grid` a 3×3×41 field into `00254.xml`, write, re-read with warpylib, evaluate; (iv) a synthetic `UseTilt`-False case.
5. `from_warp_xml` in torch-tilt-series, **option 3 of 0.11.3** (global-only loader first), on branch `feat/warp-xml-loader` of `~/Software/teamtomo`; tests appended to the package's existing `tests/test_io.py` (synthetic XML in `tmp_path`, no lab data). Only after phases C/D are complete.
6. Post the proposal on the TeamTomo Zulip (I/O packages get their own `teamtomo/xmlfile` repo — `CONTRIBUTING.md`), with 0.11 as evidence; then the monorepo PR (`io` extra gains `xmlfile`).
7. Follow-up PR: native Warp grid evaluation in torch-tilt-series (0.11.3, option 2).
8. Later, back in `particle_picker`/JOLT: use the helpers + the proven conventions for the G3 export (`local_alignment_BA.md` §7/§8).

### 0.11 Numerical validation against torch-tilt-series (2026-09-17)

Setup (laptop): `~/Software/xmlfile-validation/` — plain folder, not a repo —
with `.venv` (uv, Python 3.12): `torch` (CPU), **`torch-tilt-series` editable
from `~/Software/teamtomo/packages/primitives/torch-tilt-series`** (clone of
upstream at `2d9f20c`, branch `feat/warp-xml-loader`, untouched), `xmlfile`
editable from `main`, `lxml starfile pandas mrcfile imodmodel matplotlib`.
Reference model = the vendored warpylib in
`particle_picker/src/external/warpylib_min` (Warp-exact, imported by path).
Scripts `scripts/common.py`, `phase_a_global.py`, `phase_a2_zflip.py`,
`phase_b_local.py`, results in `output/phase*/`. Data: `particle_picker/data/
EMPIAR-10499/warp/warp_tiltseries/00254.xml` (fiducial etomo import,
`AxisAngle` −4.2999735° = the IMOD `.xf` rotation exactly; 1×1×1 grids;
`ImageDimensionsAngstrom` 6526.5 × 6308.9; 10 Å/px `tiltstack/00254/00254.st`
41 × 630 × 652 with `.fid`/`.prexg`/`.xf`) and `data/bmp6/WARP_DEV_TEST/
TS_042.xml` (M-refined, 6×4×36 `GridMovement`, `ImageDimensionsAngstrom`
"0, 0" so dims are supplied explicitly to both sides).

#### 0.11.1 Phase A — global mapping (settles open decision F)

500 random volume points, 64 sign/order/flip hypotheses. Exactly two are
exact (**0.0001 px RMS**; the next best 112 px) and they are the same model:
negate the tilt angles ⇔ flip volume z. The clean expression uses the field
torch-tilt-series provides for this: `levelled2tomo = diag(−1, 1, 1, 1)` (zyx
z-flip), tilt angles untouched (`phase_a2_zflip.py`: 0.0001 px; without the
flip 512 px).

| `TiltSeries` | Warp XML | verified |
| --- | --- | --- |
| `tilt_angles` | `Angles` | as is |
| `tilt_axis_angle` | `AxisAngle` | as is, per tilt |
| `sample_translations` (Å, `(y, x)`) | `(AxisOffsetY, AxisOffsetX)` | **Å, sign +, no swap** |
| `levelled2tomo` | z-flip | Warp tomogram z = −(torch-tilt-series sample z) |
| `pixel_spacing` | `CTF/Param[PixelSize]` | 1.7005 Å |
| `image_indices` | `UseTilt` | all True in the test files |
| `project_points` output (yx, Å, centre) | Warp image coords − `ImageDimensionsAngstrom/2`, xy | swap axes |

xmlfile's parsed values (angles, axis angle, offsets, dims, pixel size) are
bit-identical to warpylib's lxml parse.

#### 0.11.2 Phase B — local 2-D grids

`grid_to_array(GridMovementX).ravel()` == warpylib `CubicGrid.values` exactly.
With `local_shifts_2d(projected_yx)` = **−(GridMovementX, GridMovementY)**
evaluated (Warp interpolating cubic spline, via warpylib) at the pre-shift
projected position normalised by `ImageDimensionsAngstrom` (not dims − 1 px),
`t = i/(T−1)` over all tilts: **0.0002 px RMS, max 0.0006** against warpylib on
a 7.9 px RMS local signal; wrong sign or swapped channels ≥ 9.6 px.

Found on the way: M also writes a 4-D `GridVolumeWarpX/Y/Z` (x, y, z, dose;
1.3–2.2 Å RMS in TS_042, 1.7 px projected). torch-tilt-series has no per-tilt
3-D hook (`local_shifts` is tilt-independent), so it is **out of scope** and
was zeroed in the reference for this phase. warpylib does not apply
`MagnificationCorrection`, so that attribute is untested either way.

#### 0.11.3 Decision: how `from_warp_xml` handles the grids (JC, 2026-09-17)

The 2-D grid is an *interpolating* einspline (per-grid coefficient solve, then
B-spline evaluation, degenerate 1-sized axes handled specially); the monorepo
loader cannot depend on warpylib. Options considered: (1) global-only loader
with a `local_shifts_2d` argument the caller supplies; (2) native evaluation in
the loader (~100–150 lines: port of the coefficient solve + evaluation with the
monorepo's `torch-cubic-spline-grids`, verified by the phase-B test);
**(3) = 1 now, 2 as a follow-up PR — chosen.** Consequence for a user: an XML
whose `GridMovementX/Y` are non-trivial loads with the global model only, and
the loader must **warn** (never silently ignore), telling the user to pass
`local_shifts_2d`; `GridVolumeWarp` is documented as unsupported.

#### 0.11.4 Phase C — perturb through xmlfile, reload, compare (done)

`scripts/phase_c_perturb.py`, 00254, 500 random points, perturbations quoted in
the 10 Å/px stack pixels. Each variant is written with xmlfile only
(`list_to_text` / `array_to_grid(template=old)`), byte-diffed, then reloaded
by **both** warpylib and the candidate:

| variant | lines changed in the XML | candidate vs warpylib | (P₁ − P₀) vs analytic expectation | mean \|Δ\| |
| --- | --- | --- | --- | --- |
| `AxisOffsetX/Y` += random ±3 px per tilt | 82 (= 2 × 41, expected) | 0.0001 px | **0.0000 px** (Δ = the injected offset, identical for every point) | 1.54 px |
| `AxisAngle` += 1° | 41 | 0.0001 px | **0.0001 px** (rotation of P₀ − offset by +1° about the image centre; Warp's ZYZ matrix is a standard rotation by −psi = +axis) | 2.07 px |
| `GridMovementX/Y` 1×1×1 → injected zero-mean 3×3×41 field, amplitude 3 px | 779 (element replaced, line count differs) | 0.0002 px | **0.0000 px** (Δ = −field at the pre-shift position); the grids read back through `grid_to_array` are bit-identical to what was injected | 1.01 px |

Outputs: `output/phaseC/00254_{offsets,axisangle,grid3x3}.xml`, `results.json`,
`phaseC_projections.npz`.

#### 0.11.5 Phase D — IMOD beads through the loaded `TiltSeries`, .mod output (done)

`scripts/phase_d_beads.py`. The 17 `.fid` tracks (697 observations, tracked on
`00254_preali.mrc`) → inverse `.prexg` → raw `00254.st` frame (px) → Å relative
to the image centre → each bead triangulated by least squares through the
candidate `TiltSeries` (the global model is affine in the point, so `A_t p +
b_t` is probed from `project_points`) → reprojected.

* Bead reprojection RMS **0.731 px** (per bead 0.53–1.09, median 0.63), mean
  residual vector (0.000, 0.000) — **identical to the IMOD fiducial solution
  scored on the `.xf` by `particle_picker/scripts/score_xf_beads.py`
  (0.731 px)**. The XML alignment loaded through xmlfile + torch-tilt-series is
  therefore the same alignment IMOD produced, to the precision of the bead
  tracks. The alternative y orientation gives 10.0 px, so there is **no y-flip**
  between IMOD model coordinates on the Warp `ts_stack` output and Warp's own
  image frame. Bead z range −130 … +91 px (centred).
* Perturbed XMLs from phase C reprojected on the same beads: offsets → Δ equals
  the injected offset to 0.0000 px; grid → 0.98 px mean displacement.
* `output/phaseD/beads_00254.mod` (imodmodel): object 0 = observed `.fid` in the
  raw frame, 1 = reprojected baseline, 2 = +offsets, 3 = +axis angle, 4 =
  +3×3 grid. View with `3dmod particle_picker/data/EMPIAR-10499/warp/
  warp_tiltseries/tiltstack/00254/00254.st beads_00254.mod`.
  `overlay_00254.png`: views 0 / 20 / 40 — observed circles sit on the gold
  beads, baseline `+` coincides, perturbed markers are displaced by 1–3 px.

#### 0.11.6 Phase E/F — the real loader, end to end through torch-reconstruct-tomogram (done)

`from_warp_xml` (uncommitted, branch `feat/warp-xml-loader`; 0.12) on real data
(`scripts/phase_e_loader.py`): `00254.xml` global 0.0001 px vs warpylib with no
warning; phase-C 3×3 file and M-refined `TS_042.xml` warn without a callable
and give 0.0002 px with the validated closure passed as `local_shifts_2d`.

Full workflow (`scripts/phase_f_workflow.py`, `phase_f_compare.py`,
`phase_f_metrics.py`): `from_warp_xml(00254.xml, image_path=00254.st)` →
`ts.pixel_spacing = 10.0` (the local stack is 10 Å/px; the XML `PixelSize` is
the 1.7 Å raw-frame pixel — see API note in 0.12) → `load_tilt_series_images`
→ `torch_reconstruct_tomogram.reconstruct_tomogram(volume_shape=(340, 630,
652), sidelength=128)` — same shape/pixel as the existing IMOD/AreTomo/JOLT
tomograms of this series. 150 s per volume on 8 CPU threads. The
reconstruction places every patch with `tilt_series.project_points`, so
`local_shifts_2d` **is honoured** (per patch centre) in reconstruction too.

Result: the volume is **slice-for-slice in the same frame as IMOD's
`etomo_fids.mrc`** (same z index, same xy; `slices_baseline_vs_etomo.png`),
and the 17 IMOD beads reconstruct as round dark discs exactly at the voxels
predicted from the phase-D bead fit (`bead_crops.png`, with perturbed
variants for comparison). Per-bead metrics (`bead_metrics.json`):

| volume | disc contrast (r ≤ 4 vs 6–8, / volume std) | correlation of the 17-px bead crop with IMOD's (median / min) |
| --- | --- | --- |
| Warp XML → torch, baseline | 8.0 (min 6.2) | **0.883** / 0.779 |
| … XML with `AxisOffset` ± 3 px per tilt | 4.4 | 0.635 |
| … XML with an injected 3×3 grid, 3 px (via `local_shifts_2d`) | 6.4 | 0.797 |
| IMOD `etomo_fids.mrc` (weighted back-projection, its own filters) | 13.9 | 1 |

Sharpness degrades monotonically with the injected misalignment and the
grid is demonstrably applied through the whole chain (XML → xmlfile →
loader → projection → reconstruction). The absolute contrast difference to
IMOD is the reconstruction method/filtering (Fourier slice insertion + DC-free
bandpass vs. WBP), not alignment.

#### 0.11.7 What this means for the next steps

* No change to xmlfile was needed for any phase; the helpers and the
  byte-exact writer are sufficient for reading and editing Warp alignments.
* The loader (`from_warp_xml`, option 3) can now be written from the table in
  0.11.1 with no open convention; its unit test asserts exactly those
  mappings on a synthetic XML.
* For `particle_picker`/JOLT's G3 export (later): write `GridMovementX/Y` with
  `array_to_grid(template=old)` in Warp's raw frame in Å with the field
  **negated** (Warp subtracts), sampled at the pre-movement position, node
  t-axis = file tilt order; `AxisOffsetX/Y` in Å as (x, y) added after
  rotation; keep `AxisAngle` = the IMOD `.xf` rotation.

### 0.12 `from_warp_xml` — committed, and the release sequence (2026-09-17)

**Committed** in `~/Software/teamtomo`, branch `feat/warp-xml-loader`, commit
`c84ba36` "feat(torch-tilt-series): from_warp_xml loader for Warp/M tilt-series
XML via xmlfile" (off upstream `2d9f20c`; not pushed, no fork yet). Four files
(+170 / −6): `packages/primitives/torch-tilt-series/{src/torch_tilt_series/
io.py, src/torch_tilt_series/__init__.py, pyproject.toml, tests/test_io.py}`.

```python
from_warp_xml(
    xml_path, pixel_spacing=None, image_path=None, local_shifts_2d=None, device="cpu"
) -> TiltSeries
```

* Same shape as `from_aretomo_output(aln_path, pixel_spacing, image_path,
  device)`; lazy `import xmlfile`; parses `Angles`, `AxisAngle`,
  `AxisOffsetX/Y`, `UseTilt`, CTF `PixelSize` with the xmlfile helpers.
* `sample_translations = (AxisOffsetY, AxisOffsetX)` Å; `levelled2tomo` =
  z-flip; `UseTilt=False` tilts dropped and the kept ones become
  `image_indices` (as the etomo loader drops excluded views).
* `pixel_spacing`: **only** the Å-per-pixel of the images at `image_path`;
  defaults to the XML `PixelSize` (raw-frame pixel); pass it for a binned
  stack (10 Å for the `ts_stack` output). The Å alignment is untouched —
  verified: argument vs attribute set gives bit-identical reconstructions
  (max |diff| 4e-8).
* `local_shifts_2d` passthrough; warns when `GridMovementX/Y` is non-zero and
  none is given; `GridVolumeWarp` documented as ignored (0.11.3).
* Tests (appended to the package's `tests/test_io.py`, synthetic XML in
  `tmp_path`): global fields + pixel-spacing override, `UseTilt=False`
  dropping, warning without / no warning with a callable. Package suite 47
  passed; ruff + ruff-format clean; mypy adds three errors of the kind the
  existing loaders already have (numpy arrays passed where `Tensor` is typed).

**Why nothing about xmlfile's hosting matters for the code:** `io.py` imports
`xmlfile` by name; the editable install used for all of 0.11 is the same code
path a PyPI or `teamtomo/xmlfile` install gives. What matters is
*installability*: the monorepo's CI runs `uv sync --locked`, and `io = [...,
"xmlfile"]` cannot resolve while xmlfile is unreleased and its repo private.

**Release sequence (order matters):**

1. ~~Commit the loader locally~~ — `c84ba36`.
2. **Zulip post** (imagesc.zulipchat.com, channel TeamTomo): xmlfile as a new
   I/O package (repo under the org per `CONTRIBUTING.md`), the loader, and
   0.11 as evidence. Ask: (a) create `teamtomo/xmlfile` (transfer of
   `jtcarrion/xmlfile`) or keep it under the author; (b) should the loader PR
   wait for the PyPI release; (c) the native grid evaluator (0.11.3 option 2)
   using `torch-cubic-spline-grids` as a follow-up — acceptable dependency?;
   (d) `GridVolumeWarp`: is a per-tilt 3-D hook in `TiltSeries` wanted?
3. **xmlfile v0.0.1 on PyPI**: make the repo public; register it as a PyPI
   trusted publisher (project `xmlfile`, workflow `ci.yml`, environment none);
   tag `v0.0.1` on `main` and push the tag — the alnfile-derived CI builds,
   inspects (`core-metadata-version = "2.4"` pin) and publishes. The version
   comes from the tag (hatch-vcs). If the repo has moved to the org first,
   register the publisher under that path instead.
4. Monorepo: fork `teamtomo/teamtomo`, push `feat/warp-xml-loader`, `uv lock`
   (new dependency), `uv run --group dev pre-commit run --all-files`, open the
   PR against `main`.
5. Follow-up PR: native grid evaluation (0.11.3 option 2).
6. Then back to `particle_picker`/JOLT: G3 export with the helpers and the
   conventions of 0.11.1/0.11.7.

### 0.10 HPC-only resources (will not exist elsewhere)

- `xmlfile/test_xml_files/`: unsanitised originals `00269.xml`, `00316.xml` (EMPIAR-10499) and `TS_001.xml` (bmp6, unpublished). Gitignored.
- Corpus directories, all verified byte-exact (201 files total):
  `processing/bmp6/warp_tiltseries` (98 files), `processing/bmp6/warp_tiltseries_ssedorAlign` (13-root-attribute workflow),
  `processing/EMPIAR-10491-5TS/warp_tiltseries`. All under `/orcd/data/mbathe/001/jcarrion/`.
  Run: `pytest tests/test_corpus.py --xml-corpus <dir>`.
- `xmlfile/.venv`: Python 3.12 with pytest. In non-interactive shells run
  `source /usr/share/lmod/lmod/init/bash && module load miniforge/25.11.0-0` first.
- Network from the HPC: GitHub works (SSH authenticates as `jtcarrion`); PyPI is blocked.
- Laptop-only: `particle_picker/data/bmp6/WARP_DEV_TEST/TS_0{34,41,42,53,61,63,65,88,91}.xml` (M-refined, 6×4×T grids, unpublished) and `data/EMPIAR-10499/etomo_patches_test/00254.xml`; the monorepo checkout used for 0.6 lives in the session scratchpad (`teamtomo/`, `alnfile/`), not in any repo.

---

## 1. Decision from TeamTomo developer discussion

> **Confirmed (2026-09-10):** TeamTomo's `CONTRIBUTING.md` says I/O packages get their own repo under the organization, requested via Zulip, rather than going into the monorepo. See section 0.6.

The agreed direction is:

- Build a separate lightweight I/O repository, not a processing package inside the main `teamtomo/teamtomo` monorepo.
- Follow the `starfile` pattern:
  - public API: `read`, `write`, and `to_string`
  - internal parser/writer classes
  - passive data containers
  - round-trip tests
- Start simple and correct.
- Preserve XML structure and ordering robustly before adding convenience features.

## 2. TeamTomo resources reviewed

### TeamTomo website

Source: <https://teamtomo.org/>

Relevant principles:

- TeamTomo is organized around modular Python packages for cryo-EM/cryo-ET.
- The website emphasizes simple, composable packages that make it easier to work with cryo-EM data in Python.
- Target users include scientists scripting around metadata and methods developers who do not want to reimplement basic infrastructure.

Implication for `xmlfile`:

`xmlfile` should be a small composable utility, not a full XML-to-reconstruction workflow.

### Input/output package overview

Source: <https://teamtomo.org/site/io_packages/>

Existing metadata I/O packages listed by TeamTomo include:

- `starfile` — read and write STAR files
- `imodmodel` — read and write IMOD model files
- `mdocfile` — read and write SerialEM metadata files
- `alnfile` — read AreTomo alignment files
- `etomofiles` — read IMOD etomo alignment files
- `dynamotable` — read and write Dynamo table files

Implication for `xmlfile`:

A Warp-style XML metadata reader/writer fits the TeamTomo I/O-package family. It should not be classified as a primitive or algorithm.

### Contribution guidelines

Source: <https://teamtomo.org/site/contributing/>

Relevant principles:

- Start by discussing proposed packages on the TeamTomo Zulip.
- Packages should do one thing and do it well.
- Packages should have a simple Python API.
- Packages should be easy to install.
- Packages should be tested.
- TeamTomo recommends a modern Python packaging template with testing and PyPI deployment.
- TeamTomo documentation uses MkDocs Material.

Implication for `xmlfile`:

The first implementation should focus only on XML I/O and preservation. Tests should be included from the beginning. Documentation can start minimal but should be compatible with TeamTomo documentation conventions.

### TeamTomo GitHub organization

Source: <https://github.com/teamtomo>

Relevant principles:

- TeamTomo packages are small, modular, easy to install, well-scoped, Pythonic, type-hinted, and tested.
- TeamTomo projects should use the BSD 3-Clause License.
- `starfile`, `mdocfile`, `imodmodel`, `etomofiles`, and related readers are distributed as separate repositories.

Implication for `xmlfile`:

Use a separate repository with BSD 3-Clause licensing and narrow scope. Do not start inside the main monorepo unless maintainers explicitly request that later.

### `starfile` repository

Source: <https://github.com/teamtomo/starfile>

Important style points:

- `starfile` is a package for reading and writing STAR files in Python.
- Its user-facing API is simple: `read`, `write`, and `to_string`.
- Its public `__init__.py` only exports those functions.
- It uses internal `StarParser` and `StarWriter` classes.
- It exposes data as simple Python dictionaries or pandas DataFrames.
- Its internal data type is intentionally small: STAR data blocks are dictionaries or DataFrames.
- Its `pyproject.toml` uses a modern packaging setup with `hatchling`, `hatch-vcs`, `ruff`, `mypy`, `pytest`, and package metadata.

Implication for `xmlfile`:

Use `starfile` as the style template, but do not copy its dataframe-first data model exactly. XML is hierarchical and ordered, so we need passive XML tree containers.

### `torch-tilt-series`

> **Superseded (2026-09-14):** torch-tilt-series now lives in the monorepo at `teamtomo/teamtomo/packages/primitives/torch-tilt-series`. Its `io.py` and `TiltSeries` fields are mapped to Warp XML in section 0.6. See section 0.

Source: <https://github.com/teamtomo/torch-tilt-series>

Relevant boundaries:

- `torch-tilt-series` handles tilt-series geometry, alignment metadata, coordinate transforms, projection matrices, and point projection.
- Its README states that subtilt/subvolume extraction and full volume reconstruction live in `torch-reconstruct-tomogram`.
- Current loaders support AreTomo `.aln` and ETOMO directories through `alnfile` and `etomofiles`.

Implication for `xmlfile`:

`xmlfile` should not construct projection matrices or perform point projection. Later, `torch-tilt-series` can optionally provide a loader that consumes `xmlfile` output.

### `cryoet-alignment`

Sources:

- PyPI: <https://pypi.org/project/cryoet-alignment/>
- GitHub: <https://github.com/uermel/cryoet-alignment>

Relevant points:

- The package converts between IMOD, AreTomo3, cryoET Data Portal, RELION, and Warp alignment formats.
- It has a simple `read` / `write` API.
- Its Warp XML reader explicitly requires `reader="warp"`; `.xml` is intentionally not auto-inferred because XML is too generic.
- Its Warp XML implementation models only global per-tilt alignment fields: angles, tilt-axis rotation, and 2D shifts.
- It intentionally does not model local 2D warp grids, 4D volume warp grids, doses, CTF fits, and other fields; those fields are ignored on read and omitted on write.

Implication for `xmlfile`:

`cryoet-alignment` is a useful reference for parsing some Warp XML alignment fields, but it should not be the base behavior for `xmlfile`. Our package must preserve unknown and currently unmodeled XML content by default. Dropping fields is only acceptable in explicit conversion/adaptor functions with loud documentation.

## 3. Initial XML fixtures reviewed

> **Superseded (2026-09-14):** `TS_0.xml` was never found on disk, and the real `TS_069.xml` has 9 root attributes, not 13. The repository now ships one fixture, `tests/data/TS_1.xml` (EMPIAR-10491), and validates other files with `pytest --xml-corpus`. The structure described below is still representative of Warp files. See section 0.

Two uploaded example XML files should become the first test fixtures.

### `TS_0.xml`

Observed structure:

- Root tag: `TiltSeries`
- Root attributes: 12
- Child elements: 27
- Tilt count from `Angles`: 31
- Per-tilt newline-separated fields:
  - `Angles`
  - `Dose`
  - `UseTilt`
  - `AxisAngle`
  - `AxisOffsetX`
  - `AxisOffsetY`
  - `MoviePath`
  - `FOVFraction`
- `CTF` block with 21 `Param` elements
- Grid blocks with one `Node` each
- No repeated `TiltPS1D` elements
- No `OptionsCTF` block
- No `TiltSimulatedScale` elements

### `TS_069.xml`

Observed structure:

- Root tag: `TiltSeries`
- Root attributes: 13
- Child elements: 102
- Tilt count from `Angles`: 36
- Per-tilt newline-separated fields:
  - `Angles`
  - `Dose`
  - `UseTilt`
  - `AxisAngle`
  - `AxisOffsetX`
  - `AxisOffsetY`
  - `MoviePath`
  - `FOVFraction`
- `CTF` block with 21 `Param` elements
- `OptionsCTF` block with 24 `Param` elements
- 36 repeated `TiltPS1D` elements
- 36 repeated `TiltSimulatedScale` elements
- Grid blocks with larger node counts, including:
  - `GridMovementX`: 6 × 4 × 36 = 864 nodes
  - `GridMovementY`: 6 × 4 × 36 = 864 nodes
  - `GridVolumeWarpX`: 4 × 6 × 4 × 10 = 960 nodes
  - `GridVolumeWarpY`: 4 × 6 × 4 × 10 = 960 nodes
  - `GridVolumeWarpZ`: 4 × 6 × 4 × 10 = 960 nodes

Implication:

The package must preserve ordered children, repeated tags, nested `Param` lists, dense grid-node blocks, and large pair-series text blocks. A simple dictionary-only representation is not enough for the core object model.

## 4. Package name and scope

Recommended repository name:

```text
teamtomo/xmlfile
```

Recommended Python import name:

```python
import xmlfile
```

Reasons:

- Mirrors `starfile`.
- Avoids overfitting to Warp in the package name.
- Keeps room for future cryo-ET XML metadata formats.
- Avoids conflict with Python standard-library `xml`.

Alternative names to discuss only if maintainers prefer tighter scope:

```text
teamtomo/warpfile
teamtomo/warpxml
teamtomo/warp-xmlfile
```

Current recommendation:

Use `xmlfile` as the generic low-level XML I/O package. Put Warp-specific interpretation in an adapter module later.

## 5. Design goals

The package should:

1. Read XML files into passive, ordered Python objects.
2. Write those objects back to XML.
3. Preserve root attributes, attribute order, child order, repeated elements, nested elements, text, and empty elements.
4. Provide `read`, `write`, and `to_string` as the main public API.
5. Keep parser/writer classes internal.
6. Provide small helper functions for common patterns after the round-trip core is stable.
7. Avoid hidden semantic conversions in the generic parser.
8. Keep dependencies minimal.
9. Use tests as the main safety net.

## 6. Explicit non-goals for the initial package

The initial package should not:

- Compute projection matrices.
- Perform tilt-series alignment.
- Reconstruct tomograms or subvolumes.
- Load image stacks.
- Depend on PyTorch.
- Depend on `torch-tilt-series`.
- Convert XML directly into `TiltSeries` as part of the generic parser.
- Drop unknown fields.
- Normalize or reorder XML content by default.
- Infer that every `.xml` file is a Warp tilt-series XML.

## 7. Proposed repository layout

> **Superseded (2026-09-14):** The actual layout is listed in section 0.4 (it adds `tests/test_edge_cases.py`, `tests/test_errors.py`, `tests/test_corpus.py`, `tests/conftest.py`, `.gitattributes`, and uses `tests/data/TS_1.xml`). There is no `adapters/` directory, and none is planned for v0.0.1. See section 0.

```text
xmlfile/
  README.md
  LICENSE
  pyproject.toml
  src/
    xmlfile/
      __init__.py
      functions.py
      models.py
      parser.py
      writer.py
      typing.py
      utils.py
      py.typed
  tests/
    data/
      TS_0.xml
      TS_069.xml
    test_read.py
    test_write.py
    test_round_trip.py
    test_models.py
    test_helpers.py
```

Potential later layout:

```text
src/xmlfile/adapters/
  __init__.py
  warp.py
```

Do not add `adapters/` until the generic core passes tests.

## 8. Proposed public API

The first public API should be intentionally small:

```python
import xmlfile

doc = xmlfile.read("TS_069.xml")
xmlfile.write(doc, "copy.xml")
text = xmlfile.to_string(doc)
```

`src/xmlfile/__init__.py` should be close to:

```python
from .functions import read, write, to_string
from .models import XmlDocument, XmlElement
```

Optional later exports:

```python
from .functions import from_string
```

Only export additional helpers once there is a clear need.

## 9. Proposed passive data model

### Core scalar type

Initial values should be preserved as strings by default. Numeric conversion should happen only in explicit helper functions.

```python
Scalar = str | None
```

Do not automatically coerce XML attribute values into `int`, `float`, or `bool` in the base parser. XML stores strings. Automatic coercion can silently corrupt formatting, precision, or intentional string values.

### `XmlDeclaration`

```python
from dataclasses import dataclass

@dataclass
class XmlDeclaration:
    version: str = "1.0"
    encoding: str = "utf-8"
    standalone: str | None = None
    quote: str = '"'
```

Purpose:

- Preserve XML declaration values.
- Avoid accidentally changing declaration style unless the writer is explicitly configured to normalize formatting.

### `XmlElement`

```python
from dataclasses import dataclass, field

@dataclass
class XmlElement:
    tag: str
    attributes: dict[str, str] = field(default_factory=dict)
    text: str | None = None
    children: list["XmlElement"] = field(default_factory=list)
    tail: str | None = None
```

Important behavior:

- Preserve child order using a list.
- Preserve attribute insertion order using Python dictionaries.
- Preserve repeated tags naturally through `children`.
- Preserve text as raw strings.
- Preserve `tail` text if needed for faithful round-trip behavior.

Optional convenience methods, if kept simple:

```python
element.findall("TiltPS1D")
element.find("CTF")
element.get("PixelSize")
```

These should be navigation helpers only. They should not perform scientific interpretation.

### `XmlDocument`

> **Superseded (2026-09-14):** `XmlDocument` also has `byte_order_mark`, `prologue_tail` and `epilogue`, which byte-exact output needs, and `filename` is excluded from equality. See section 0.

```python
@dataclass
class XmlDocument:
    root: XmlElement
    declaration: XmlDeclaration | None = None
    filename: Path | None = None
```

The document should be a passive container.

## 10. Parser design

### `functions.py`

Responsibilities:

```python
def read(filename, *, preserve_whitespace=True) -> XmlDocument:
    parser = XmlParser(filename, preserve_whitespace=preserve_whitespace)
    return parser.document


def to_string(document, **kwargs) -> str:
    return XmlWriter(document, **kwargs).to_string()


def write(document, filename, **kwargs) -> None:
    XmlWriter(document, filename=filename, **kwargs).write()
```

Keep this layer thin, like `starfile.functions`.

### `parser.py`

> **Superseded (2026-09-14):** The parser uses `xml.parsers.expat`, not `ElementTree`, because ElementTree deletes `xmlns` declarations. It also refuses external entities and warns (`XmlLossyContentWarning`) when it drops comments or processing instructions. See section 0.

Responsibilities:

- Validate that the path exists.
- Read text with the correct encoding.
- Parse XML declaration if present.
- Parse root and all descendants into `XmlDocument` / `XmlElement`.
- Preserve element order, attributes, repeated tags, text, and tail.
- Raise clear errors for malformed XML.

Potential implementation options:

1. Standard library `xml.etree.ElementTree`
   - Pros: no dependency.
   - Cons: does not preserve comments or every formatting detail perfectly.

2. `lxml`
   - Pros: stronger support for comments, processing instructions, line numbers, and richer parsing.
   - Cons: additional dependency and potentially less lightweight.

Initial recommendation:

Start with the standard library unless tests show that preserving comments, processing instructions, or more detailed formatting is required. The provided fixtures do not require comments or namespaces for the first version.

### `writer.py`

> **Superseded (2026-09-14):** `indent` defaults to `None` (verbatim, byte-exact output); passing `indent="  "` pretty-prints. `write` also takes `byte_order_mark` and `overwrite` (default `True`). See section 0.

Responsibilities:

- Serialize `XmlDocument` / `XmlElement` back to XML.
- Preserve child order.
- Preserve repeated sibling order.
- Preserve attribute order.
- Preserve text values without numeric reformatting.
- Write to disk only when explicitly requested.

Writer options to consider:

```python
def to_string(
    document: XmlDocument,
    *,
    encoding: str | None = None,
    xml_declaration: bool = True,
    indent: str = "  ",
    preserve_empty_elements: bool = True,
) -> str:
    ...
```

Avoid adding too many formatting options in the first PR. Start with the options needed to safely round-trip the fixtures.

## 11. Helper utilities after core round-trip

> **Status (2026-09-14):** Not started. In scope for v0.0.1, and pandas is allowed. Consider designing these against the torch-tilt-series mapping in section 0.6 (open decision C).

Add helpers only after the generic XML core is stable.

### List-like text fields

Warp-style tilt-series XML uses newline-separated text fields:

- `Angles`
- `Dose`
- `UseTilt`
- `AxisAngle`
- `AxisOffsetX`
- `AxisOffsetY`
- `MoviePath`
- `FOVFraction`

Proposed helpers:

```python
def text_to_list(element: XmlElement, dtype=str) -> list:
    ...


def get_child_text_list(parent: XmlElement, tag: str, dtype=str) -> list:
    ...
```

Safety rule:

These helpers may coerce values, but the base parser must not.

### `Param` blocks

Common XML pattern:

```xml
<Param Name="PixelSize" Value="1.3680"/>
```

Proposed helper:

```python
def params_to_dict(element: XmlElement) -> dict[str, str]:
    ...
```

Safety rule:

If duplicate `Name` values occur, do not silently overwrite by default. Either return a list of pairs or raise unless `allow_duplicates=True`.

### Grid blocks

Common XML pattern:

```xml
<GridMovementX Width="6" Height="4" Depth="36" MarginX="0" MarginY="0" MarginZ="0">
  <Node X="0" Y="0" Z="0" Value="..."/>
</GridMovementX>
```

Proposed helper:

```python
def grid_to_dataframe(element: XmlElement):
    ...
```

Potential output columns:

```text
X
Y
Z
W
Value
```

Safety checks:

- Preserve node order.
- Check `len(nodes) == Width * Height * Depth` when no `Duration` is present.
- Check `len(nodes) == Width * Height * Depth * Duration` when `Duration` is present.
- Do not reshape into a NumPy array until dimension order is documented and tested.

### Pair-series text fields

Common XML pattern:

```xml
<TiltPS1D ID="0">0|14417.534;0.001953125|3488.794;...</TiltPS1D>
```

Proposed helper:

```python
def parse_pair_series(element: XmlElement):
    ...
```

Potential dataframe columns:

```text
x
y
```

For repeated per-tilt series:

```python
def repeated_pair_series_to_dataframe(parent: XmlElement, tag: str):
    ...
```

Potential output columns:

```text
id
x
y
```

Safety checks:

- Preserve input order.
- Do not assume IDs are continuous unless explicitly validated.
- Raise clear errors for malformed `x|y` pairs.

## 12. Warp-specific adapter layer, later

> **Superseded (2026-09-14):** A Warp adapter is **not** planned for xmlfile v0.0.1 (decision 6). Warp interpretation is expected to live downstream in torch-tilt-series (`from_warp_xml`). See section 0.

Only after the generic XML package is robust, add:

```text
src/xmlfile/adapters/warp.py
```

Potential functions:

```python
def is_warp_tilt_series_xml(doc: XmlDocument) -> bool:
    ...


def tilt_table(doc: XmlDocument):
    ...


def ctf_parameters(doc: XmlDocument):
    ...


def options_ctf_parameters(doc: XmlDocument):
    ...


def grids(doc: XmlDocument):
    ...


def tilt_ps1d(doc: XmlDocument):
    ...
```

Important boundary:

These adapter functions should expose structured metadata. They should not construct a `torch_tilt_series.TiltSeries` in the base XML package.

Potential future integration should live in `torch-tilt-series`:

```python
from torch_tilt_series.io import from_warp_xml
```

That loader can depend optionally on `xmlfile` and map selected metadata into `TiltSeries` fields.

## 13. Testing plan

### Test category 1: basic read

> **Superseded (2026-09-14):** Fixture counts now come from `TS_1.xml`: 9 root attributes, 112 children, 41 tilts, CTF 21, OptionsCTF 24, TiltPS1D 41, TiltSimulatedScale 41, GridMovementX and GridVolumeWarpX 984 nodes each. See section 0.

Tests:

- Read `TS_0.xml`.
- Read `TS_069.xml`.
- Root tag is `TiltSeries`.
- Root attributes are preserved.
- First child order is preserved.
- Repeated tags are preserved.

Expected fixture-specific checks:

```text
TS_0.xml:
  root attributes = 12
  child elements = 27
  nonempty Angles entries = 31
  CTF Param count = 21

TS_069.xml:
  root attributes = 13
  child elements = 102
  nonempty Angles entries = 36
  CTF Param count = 21
  OptionsCTF Param count = 24
  TiltPS1D count = 36
  TiltSimulatedScale count = 36
```

### Test category 2: semantic round-trip

> **Superseded (2026-09-14):** Byte-for-byte equality **is** tested and passes, in addition to semantic equality. See section 0.

Tests:

```python
original = xmlfile.read(path)
text = xmlfile.to_string(original)
copy = xmlfile.from_string(text)
assert copy == original
```

Semantic identity must include:

- root tag
- root attributes and their order
- child order
- repeated element order
- element text
- nested children
- nested attributes

Do not require byte-for-byte equality in PR 1.

### Test category 3: write/read round-trip

Tests:

```python
doc = xmlfile.read(path)
xmlfile.write(doc, tmp_path / "copy.xml")
copy = xmlfile.read(tmp_path / "copy.xml")
assert copy == doc
```

### Test category 4: helper functions

Tests after helper functions are added:

- `text_to_list(Angles, float)` length matches tilt count.
- `text_to_list(UseTilt, bool)` returns booleans only when requested.
- `params_to_dict(CTF)` includes `PixelSize`.
- `grid_to_dataframe(GridMovementX)` returns 864 rows for `TS_069.xml`.
- `grid_to_dataframe(GridVolumeWarpX)` returns 960 rows for `TS_069.xml`.
- `parse_pair_series(TiltPS1D[0])` returns expected number of pairs.
- duplicate `Param Name` entries are handled explicitly.

### Test category 5: malformed XML and safety failures

Tests:

- Missing file raises `FileNotFoundError`.
- Malformed XML raises a useful parse error.
- Helper with wrong expected count raises `ValueError`.
- Duplicate params do not silently overwrite unless explicitly allowed.
- `write(..., overwrite=False)` refuses to overwrite existing files if that option is implemented.

## 14. Safety checks for coding

### Preservation safety

- Never drop unknown elements in the generic parser.
- Never drop unknown attributes in the generic parser.
- Never reorder children.
- Never reorder repeated tags.
- Never convert values to numeric types in the base parser.
- Never normalize scientific values in the base writer.
- Preserve large text blocks as text in the core model.

### File safety

> **Superseded (2026-09-14):** `write` overwrites by default (decision 7); `overwrite=False` refuses. Fixture paths are sanitised. See section 0.

- Do not overwrite user files by default if an `overwrite` option is added.
- Use temporary files in tests.
- Keep fixture paths anonymized if needed before committing.
- Avoid storing lab-specific absolute paths in public fixtures unless approved.

### Scientific safety

- Do not guess pixel size.
- Do not infer units silently.
- Do not assume `AxisOffsetX/Y` are pixels; in Warp-style files these can be Angstrom-style metadata depending on context.
- Do not assume XML fields are aligned unless lengths are checked.
- Do not assume `TiltPS1D ID` values are continuous without validation.
- Do not reshape grids until axis order is documented.
- Do not discard local movement/volume-warp grids.

### Scope safety

- Keep `xmlfile` independent of PyTorch.
- Keep `xmlfile` independent of reconstruction code.
- Keep `xmlfile` independent of `torch-tilt-series` in PR 1.
- Put scientific adapters behind explicit function names.
- Make lossy conversions explicit and documented.

### API safety

- Keep the top-level API small.
- Do not auto-infer that `.xml` means Warp XML unless maintainers explicitly request this later.
- If a format-specific reader is added, require an explicit call such as `xmlfile.adapters.warp.read_tilt_series_xml(...)`.

### Dependency safety

> **Superseded (2026-09-14):** pandas is accepted as a dependency (decision 5). The core currently has no runtime dependencies. The Python floor (3.10 or 3.11) is open decision B. See section 0.

Start with:

- Python >= 3.11
- standard library XML parser
- `pytest` for tests
- `ruff` and `mypy` for development

Add later only if necessary:

- `pandas` for DataFrame helpers
- `lxml` if comments, processing instructions, namespaces, or exact formatting become required
- `numpy` only if grid array conversion is added

Avoid in the base package:

- `torch`
- `mrcfile`
- `starfile`
- `torch-tilt-series`
- reconstruction packages

## 15. Implementation milestones

### Milestone 0: repository/bootstrap

> **Status (2026-09-14):** Mostly done. Editable install, ruff and mypy never ran (no PyPI on the HPC); no CI; not generated from the TeamTomo template. See sections 0.3, 0.7 and 0.8.

Goal:

Create the separate repository and package skeleton.

Tasks:

- Create `teamtomo/xmlfile` or local fork equivalent.
- Use the TeamTomo-preferred Python packaging template if maintainers provide one.
- Use BSD 3-Clause License.
- Add minimal README.
- Add `pyproject.toml` with test/dev tooling.
- Add `py.typed` if type hints are included.

Validation:

```bash
python -m pip install -e .[test]
pytest
```

### Milestone 1: generic ordered XML object model

> **Status (2026-09-14):** Done, validated on `TS_1.xml` and 201 local files, byte-exact.

Goal:

Read and write XML without losing structure.

Tasks:

- Implement `XmlDeclaration`.
- Implement `XmlElement`.
- Implement `XmlDocument`.
- Implement `XmlParser`.
- Implement `XmlWriter`.
- Implement `read`, `write`, `to_string`, and optionally `from_string`.

Validation:

- `TS_0.xml` read test passes.
- `TS_0.xml` semantic round-trip passes.
- `TS_069.xml` read test passes.
- `TS_069.xml` semantic round-trip passes.

### Milestone 2: helper utilities for common XML patterns

> **Status (2026-09-14):** Not started; in scope for v0.0.1.

Goal:

Add safe utilities without changing the core object model.

Tasks:

- Add `text_to_list`.
- Add `params_to_dict` or `params_to_pairs`.
- Add `grid_to_dataframe` if `pandas` is accepted as a dependency.
- Add `parse_pair_series`.

Validation:

- All helper-specific tests pass on both fixtures.
- Helper failures raise clear errors.

### Milestone 3: Warp tilt-series adapter

> **Superseded (2026-09-14):** Dropped from xmlfile v0.0.1 (decision 6). See section 0.

Goal:

Provide convenient structured access to Warp-style tilt-series XML metadata.

Tasks:

- Add `xmlfile.adapters.warp`.
- Add `is_warp_tilt_series_xml`.
- Add `tilt_table`.
- Add `ctf_parameters`.
- Add `options_ctf_parameters`.
- Add `grid_summary` or `grids`.

Validation:

- `tilt_table(TS_0)` returns 31 rows.
- `tilt_table(TS_069)` returns 36 rows.
- CTF parameter extraction preserves all names/values.
- Grid summaries match fixture counts.

### Milestone 4: optional downstream integration

Goal:

Let `torch-tilt-series` consume XML metadata only when maintainers are ready.

Potential location:

```text
torch-tilt-series/src/torch_tilt_series/io.py
```

Potential API:

```python
def from_warp_xml(xml_path, pixel_spacing=None, image_path=None, device="cpu"):
    ...
```

Important:

This is not part of the first `xmlfile` PR.

## 16. Proposed first PR scope

> **Superseded (2026-09-14):** No PR is planned against the monorepo: TeamTomo creates a separate repo for I/O packages, requested via Zulip. v0.0.1 is expected to include the M2 helpers (decision 6). See section 0.

Keep the first PR narrow:

```text
Add generic ordered XML read/write round-trip support
```

Included:

- `XmlDeclaration`
- `XmlElement`
- `XmlDocument`
- `XmlParser`
- `XmlWriter`
- `read`
- `write`
- `to_string`
- `from_string` if useful for tests
- fixtures, possibly anonymized
- read and round-trip tests

Excluded:

- DataFrame helpers
- Warp adapter
- `torch-tilt-series` integration
- grid reshaping
- pixel-size inference
- alignment conversion
- reconstruction functionality

## 17. Proposed first README outline

```markdown
# xmlfile

Read and write XML metadata files in Python.

`xmlfile` is a lightweight TeamTomo-style I/O package modeled after `starfile`.
It provides a small API for reading XML into passive ordered Python objects and
writing those objects back to XML.

## Installation

```bash
pip install xmlfile
```

## Quickstart

```python
import xmlfile

doc = xmlfile.read("TS_069.xml")
xmlfile.write(doc, "copy.xml")
text = xmlfile.to_string(doc)
```

## Design

The core parser preserves XML structure. It does not interpret cryo-ET metadata,
compute alignment models, or perform scientific conversion.
```

## 18. Suggested coding sequence

> **Superseded (2026-09-14):** Steps 1–8 are done (with `TS_1.xml` as the fixture). In step 9, only pytest has run; ruff and mypy have not. See section 0.

1. Create repo skeleton.
2. Add `models.py` with dataclasses and equality tests.
3. Add `parser.py` with file/from-string parsing.
4. Add `writer.py` with string serialization.
5. Add `functions.py` top-level wrappers.
6. Add `__init__.py` exports.
7. Add `TS_0.xml` fixture and tests.
8. Add `TS_069.xml` fixture and tests.
9. Run `ruff`, `mypy`, and `pytest`.
10. Only then start helper functions.

## 19. Open questions for maintainers

> **Superseded (2026-09-14):** All seven have been answered by the author (section 0.5). The remaining open decisions are in section 0.8. Maintainers can still weigh in on the Zulip proposal. See section 0.

These should not block Milestone 1, but should be confirmed before public release:

1. Should the public package name be exactly `xmlfile`?
2. Are the example XML fixtures approved for public test data, or should paths/metadata be anonymized?
3. Is standard-library `xml.etree.ElementTree` acceptable for the first version?
4. Do maintainers want byte-for-byte formatting preservation eventually, or is semantic round-trip preservation enough?
5. Should `pandas` be a core dependency or an optional dependency for helper functions?
6. Should Warp-specific adapters live in `xmlfile.adapters.warp` or downstream in `torch-tilt-series` only?
7. Should writing default to refusing overwrites?

## 20. Recommended immediate next task

> **Superseded (2026-09-14):** Milestone 1 is done. The next steps are in section 0.9. See section 0.

Implement Milestone 1 only.

Success criterion:

```python
import xmlfile

doc = xmlfile.read("tests/data/TS_0.xml")
copy = xmlfile.from_string(xmlfile.to_string(doc))
assert copy == doc

doc = xmlfile.read("tests/data/TS_069.xml")
copy = xmlfile.from_string(xmlfile.to_string(doc))
assert copy == doc
```

Once that passes, the project has a safe foundation. Every future feature can be added without risking silent metadata loss.

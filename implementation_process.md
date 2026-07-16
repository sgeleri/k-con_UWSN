# Implementation Process

This document is the chronological technical decision log for the
paper-traceable implementation of:

> C. Tantur Karagul, M. B. Akgun, H. U. Yildiz, and B. Tavli,
> “Mitigating Energy Cost of Connection Reliability in UWSNs Through
> Non-uniform k-Connectivity,” IEEE Internet of Things Journal, 2025.

The implementation is developed one reviewed stage at a time according to
[`plan.md`](plan.md). Existing entries are retained when decisions change;
superseded decisions are marked explicitly.

## Record format

Each completed stage records:

- Scope completed and files changed.
- Paper sections, equations, tables, and figures used.
- Design decisions and rationale.
- Assumptions, ambiguities, and implementation-specific behavior.
- Verification commands and results.
- Differences from the paper.
- Items requiring review before the next stage.

## Initial decisions

- Repository: standalone `k-con_UWSN`.
- Initial modeling stack: PuLP with the open-source HiGHS solver.
- Gurobi is deferred to preserve the one-year academic Named-User license for
  possible later work.
- Implementation order: parameters and environment, grouped MILP constraints,
  solution extraction, runner, then figures.
- Code uses BS index `0`; the paper uses BS index `1`.
- Direct paper implementations receive nearby section/equation/table/figure
  comments and matching test references.
- Primary visual deliverables are Section IV-B Fig. 3(a) Network Topology and
  Fig. 3(b) Scenario-I.
- The paper does not publish the 12 sensor coordinates or random seed used in
  Fig. 3. The figures will be deterministic methodological reproductions, not
  claims of exact numerical or pixel-level reconstruction.

## Stage log

### Stage 0 — Minimal scaffolding

#### Scope and files

- Added `pyproject.toml` with setuptools packaging, Python 3.11+, NumPy,
  Matplotlib, pytest, and Ruff.
- Added `src/kcon_uwsn/__init__.py`, `tests/`, and
  `docs/paper_traceability.md`.
- Added `.gitignore` rules for Python, local environments, solver files, and
  generated results.
- Expanded `README.md` with project navigation and development setup.
- Created a local `.venv` and installed the package in editable mode.

#### Decisions

- NumPy supports environment calculations; Matplotlib is present now because
  Fig. 3(a)/(b) is a primary deliverable.
- PuLP and HiGHS remain deferred until Stage 5, when the first optimization
  model is introduced.
- The package uses a `src/` layout to prevent tests from accidentally importing
  code directly from the repository root.
- Generated solver and figure artifacts are ignored; source, tests, and
  documentation remain version-controlled.

#### Verification

- Editable installation completed under Python 3.13.10.
- Package tests and Ruff are configured through `pyproject.toml`.

#### Paper relationship

Stage 0 is implementation scaffolding and does not encode paper behavior.

### Stage 1 — Parameters and notation

#### Scope and files

- Added immutable `NetworkParameters`, `AcousticParameters`,
  `PowerLevelTable`, `ExperimentParameters`, and `PaperParameters` in
  `src/kcon_uwsn/params.py`.
- Added 14 focused tests in `tests/test_params.py`.
- Added Stage 1 mappings to `docs/paper_traceability.md`.

#### Paper sources

- Section III-A and Table I: timing, traffic, data rate, path, interference,
  connectivity, and deployment parameters.
- Section III-B, Eqs. (1)–(5), and Tables I–II: acoustic constants,
  transmission ranges, and published energy references.
- Fig. 1: default 30-sensor, 1×3×0.30 km deployment scale.
- Tables III–IV: `(|W_1|, |W_2|, |W_3|)` cardinality convention.

#### Decisions

- Table II energies are retained in their published mJ/bit unit for reference
  and exposed through an explicit J/bit conversion for later optimization.
- `PowerLevelTable` is reference data only. Eqs. (1)–(5) will be calculated in
  Stage 3 and checked against the published rounded values.
- `ExperimentParameters.connectivity_counts` stores partition cardinalities;
  explicit sensor membership remains a Stage 4 environment responsibility.
- Defaults use `ξ=1`, matching the value selected after the Section IV-A
  control-frequency analysis.
- Validation rejects values outside the paper's `ξ ∈ [0.25,4]` and
  `κ ∈ [1,3]` analysis ranges rather than silently extrapolating.
- All dataclasses are frozen so paper constants cannot change during a run.

#### Ambiguities and differences

- The paper gives a deployment dimension range and several configurations, not
  one universal default. The 1×3×0.30 km Fig. 1 deployment is used as the
  general default; later figure-specific settings will override it explicitly.
- The implementation uses descriptive names with units while retaining paper
  symbols in docstrings and traceability records.

#### Verification

Commands:

```shell
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

Results: 14 tests passed; Ruff reported no issues. The IDE's basedpyright
instance warns that `pytest` is unresolved because it is not currently using
the project `.venv`; pytest itself imports and runs successfully inside the
documented environment.

#### Review before Stage 2

- Confirm the parameter grouping and the 30-sensor 1×3×0.30 km default.
- Confirm that paper-range validation should remain strict.
- Stage 2 must not add energy calculations; it is limited to deployment,
  distances, and directed arc construction.

### Stage 2 — Network environment

#### Scope and files

- Added `src/kcon_uwsn/environment.py` with immutable `Deployment` and
  `NetworkEnvironment` data structures.
- Added reproducible 3D and 2D uniform deployment generation.
- Added pairwise Euclidean distance calculation and directed arc construction.
- Added a convenience builder using Table II's 1000 m maximum range.
- Exported the environment API from `src/kcon_uwsn/__init__.py`.
- Added 12 focused tests in `tests/test_environment.py`.
- Updated `docs/paper_traceability.md`.

#### Paper sources

- Section III-A: rectangular-prism deployment, uniformly distributed stationary
  sensors, static corner sonobuoy, and directed graph `G=(V,A)`.
- Section III-A graph definition: `(i,j)∈A` exactly when
  `i≠j` and `d_ij≤R_max(l_max)`.
- Fig. 1: conceptual 3D topology with one BS and 30 sensors.
- Section IV-B: 1×1 km two-dimensional cross section.
- Table II: `R_max(l_max)=1000 m`.

#### Decisions

- Coordinates are represented in meters. The chosen frame is
  `x∈[-d_x/2,d_x/2]`, `y∈[0,d_y]`, and depth `z∈[-d_z,0]`.
- The BS is at `(-d_x/2,0,0)`. This is a top corner and also yields the
  Section IV-B coordinate `(-0.5,0)` when distances are displayed in km.
- Node 0 is the BS and nodes 1 through `|W|` are sensors. This intentionally
  differs from the paper's one-based MILP notation.
- Arc construction includes the exact range boundary and excludes self-loops.
  Because distance and maximum range are symmetric at this stage, a reachable
  pair produces one arc in each direction.
- NumPy arrays are copied and marked read-only when stored in frozen environment
  objects, preventing a topology from changing while a model uses it.
- No NetworkX dependency is needed; the paper's required primitives are compact
  tuples and matrices.

#### Ambiguities and differences

- The paper specifies that the BS occupies one of four top corners but does not
  define a coordinate origin or sign convention. The selected frame is an
  implementation choice that preserves all Euclidean distances.
- Fig. 1 does not provide the random seed or sensor coordinates. Seeded NumPy
  generation provides reproducibility without claiming an exact reconstruction.
- Energy, power-level selection, and interference are deliberately absent from
  this stage.

#### Verification

Commands:

```shell
.venv/bin/python -m pytest tests/test_environment.py tests/test_params.py
.venv/bin/python -m ruff check src/kcon_uwsn/environment.py \
  src/kcon_uwsn/__init__.py tests/test_environment.py
```

Results: 26 tests passed after adding Stage 2 (12 environment tests and 14
parameter tests). Tests cover reproducibility, deployment bounds, 2D mode,
immutability, exact Euclidean distances, range-boundary inclusion, directed
arcs, disconnected sensors, and malformed input.

#### Review before Stage 3

- Confirm the coordinate convention and default top-corner BS.
- Confirm that a reachable physical pair should produce both directed arcs.
- Stage 3 will add Eqs. (1)–(5) only and validate calculated transmission
  energies against Table II.

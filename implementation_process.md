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

### Stage 3 — Acoustic energy environment

#### Scope and files

- Extended `src/kcon_uwsn/environment.py` with the acoustic calculations from
  Eqs. (1)–(5).
- Added `AcousticEnergyEnvironment`, containing calculated coefficients,
  power-level energies, Eq. (4) reception energy, and immutable per-arc
  transmission energies.
- Exported the Stage 3 API from `src/kcon_uwsn/__init__.py`.
- Added 18 focused tests in `tests/test_energy_environment.py`.
- Updated `docs/paper_traceability.md`.

#### Paper sources

- Section III-B, Eq. (1): transmission loss at `R_max(l)`.
- Section III-B after Eq. (1): `nu=10^(alpha(f_0)/10)`.
- Eq. (2): Thorp absorption coefficient.
- Eqs. (3)–(4): transmission and reception energy per bit.
- Eq. (5): minimum power-level energy for link `(i,j)`.
- Tables I–II: acoustic constants, ranges, and reference energies.

#### Decisions

- Functions accept distances in meters and explicitly apply Eq. (1)'s `10^-3`
  conversion in the absorption exponent.
- Equations (1)–(3) are authoritative. Table II is treated as rounded
  validation data rather than as the source of calculated coefficients.
- Eq. (5) uses inclusive range boundaries. A distance above 1000 m returns
  infinity, exactly as the equation states; graph arcs remain limited to
  reachable distances and therefore receive finite energies.
- Eq. (4) is represented directly by `P_r` from `AcousticParameters`.
- Per-arc energies use an immutable mapping whose keys must equal `A`.

#### Ambiguities and numerical observations

- Direct use of the printed equations gives 9.567450 mJ/bit at level 9, while
  Table II reports 9.568 mJ/bit. The 0.000550 mJ/bit difference is slightly
  larger than half of the last printed decimal unit and may result from
  intermediate precision or rounding not described in the paper.
- The implementation does not tune constants to force a match. All calculated
  levels must instead agree with Table II within 0.001 mJ/bit, one unit of its
  final published decimal place.

#### Verification

Commands:

```shell
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

Tests cover the numerical result of each equation, all ten Table II levels,
every Eq. (5) range boundary, the infinity branch, per-arc energy selection,
reception cost, immutability, and invalid inputs. Results: 44 tests passed;
Ruff and `git diff --check` reported no issues.

#### Review before Stage 4

- Confirm that calculated Eq. (1)–(3) values should remain authoritative over
  rounded Table II values.
- Confirm the documented 0.001 mJ/bit Table II comparison tolerance.
- Stage 4 will add only `W_n`/`kappa_n` assignment and Eq. (26) interference
  preprocessing.

### Stage 4 — Non-uniform connectivity and interference

#### Scope and files

- Added explicit and seeded construction of disjoint `W_n` subsets.
- Added immutable `ConnectivityPartition` with both set and per-sensor views.
- Added sparse Eq. (26) preprocessing through `InterferenceEnvironment`.
- Added complete solver-independent `EnvironmentData` and `build_environment`.
- Added 10 focused tests in `tests/test_connectivity_interference.py`.

#### Paper sources

- Section III-A: sensor subsets with subset-specific `kappa_n`.
- Constraint (18) explanation and Tables III–IV: `W_n` membership/cardinality.
- Section IV-C: random assignment of sensors to `W_n`.
- Section III-C, Eq. (26): `I^i_jm=1` iff `gamma*d_jm>=d_ji`.

#### Decisions

- Explicit sets support exact Table III scenarios. Seeded cardinality assignment
  supports the statistical configurations described in Section IV-C.
- Empty `W_n` sets are retained, making tuples such as `(30,0,0)` explicit.
- Eq. (26) is calculated literally for every node and directed arc. Only true
  indicators are stored, but a method exposes zero/one lookup.
- Literal Eq. (26) evaluation includes the transmitter (`i=j`) because
  `d_jj=0`. Stage 10 will define Constraint (22)'s interference summation
  domain without changing the precomputed equation.
- Explicit set cardinalities must match `ExperimentParameters`; inconsistent
  experiment descriptions fail before model construction.

#### Ambiguities and differences

- Section IV-C states that set membership is random but does not report the
  random seed. A seeded NumPy permutation provides reproducibility.
- The notation `A\\{i}` in Constraint (22) is not resolved in Stage 4. Eq. (26)
  coefficients remain complete so that decision can be reviewed with Stage 10.

#### Verification

Tests cover partition disjointness/coverage, invalid `kappa`, deterministic
random assignment, Eq. (26) true/false branches, transmitter behavior, sparse
storage, explicit configuration assembly, and cardinality mismatch rejection.

### Stage 5 — MILP variables, domains, and objective

#### Scope and files

- Added PuLP and open-source HiGHS to `pyproject.toml` and the local environment.
- Added `src/kcon_uwsn/model.py`.
- Defined `f`, `g`, `h`, `p`, and `epsilon` with typed immutable index maps.
- Added Objective (6) and domains from Constraints (23)–(25).
- Added 8 structural tests in `tests/test_model_stage_5.py`.

#### Paper sources

- Section III-C: decision-variable definitions.
- Objective (6): minimize `epsilon`.
- Constraints (23)–(25): integer and binary domains.

#### Decisions

- Path indices are one-based to match `l in {1,...,N_l}`; nodes remain
  zero-based under the documented environment convention.
- `epsilon` is a non-negative continuous variable. The paper defines it as
  energy and does not require integrality.
- Variable names include every mathematical index for readable LP exports.
- The current PuLP 3.3 `problem.add_variable` API is used instead of deprecated
  direct `LpVariable` construction.
- PuLP registers variables lazily when expressions reference them. Before
  Stage 6 constraints, `ModelVars` is the authoritative declaration/index map;
  only `epsilon` appears in the current problem expression.
- Solver options remain outside `model.py`; importing `highspy` confirms the
  future `pulp.HiGHS` backend is available.

#### Verification

Focused tests verify exact index counts, path/node conventions, every variable
domain, Objective (6), absence of premature constraints, immutable index maps,
and HiGHS availability. The full suite reports 62 passing tests; Ruff and
`git diff --check` report no issues. No optimization solve is expected at this
stage.

#### Review before Stage 6

- Confirm literal Eq. (26) preprocessing, including the transmitter.
- Confirm the explicit/seeded `W_n` APIs.
- Confirm one-based path indices inside otherwise zero-based code.
- Stage 6 will add only Constraints (7)–(12), one named helper per equation.

### Stage 6 — Flow construction constraints

#### Scope

- Implemented Constraints (7)–(12), which are required foundations for the
  requested Stages 7–10.
- Added one equation-numbered helper per logical constraint group.
- Added deterministic names such as `c07_flow_i0_k1_l1`.

#### Paper sources and decisions

- Constraint (7): source emits `p^l_k`, BS absorbs it, and relays balance flow.
- Constraint (8): each source generates `s_k*N_r` packets.
- Constraint (9): incoming source flow is summed only from `j in W`, matching
  the printed domain.
- Constraints (10)–(11): `f` and `h` are coupled using `s_k*N_r`.
- Constraint (12): outgoing use is at most one per node/source/path; the paper
  applies this to sensor nodes `W`, not the BS.

#### Verification

A solved fixed topology is optimal, each source delivers 1440 packets, and
every Constraint (7) residual is zero within numerical tolerance.

### Stage 7 — Path structure and disjointness

#### Scope and paper sources

- Constraint (13): each directed link is used by at most one path per source.
- Constraint (14): BS ingress flow is non-increasing with path index.
- Constraints (15)–(16): used-link flow equals `p^l_k`; unused links receive
  the paper's big-M relaxation.
- Constraints (19)–(20): each non-source sensor is an incoming/outgoing relay
  on at most one path of a source.

#### Decisions and verification

- `M=10,000` is read from Table I through `NetworkParameters`.
- A complete three-node topology with `kappa=2` solves optimally and produces
  at least two separate path starts for every sensor. Extracted relay usage
  confirms no relay appears on multiple paths for the same source.

### Stage 8 — Control traffic and non-uniform connectivity

#### Scope and paper sources

- Implemented Constraint (17) exactly as
  `g^kl_ij=xi*N_r*(h^kl_ij+h^kl_ji)`.
- Implemented Constraint (18) using the Stage 4 per-sensor `kappa` mapping.

#### Decisions and verification

- The graph generated in Stage 2 is symmetric, so Constraint (17) requires and
  validates the presence of every reverse arc.
- Model construction rejects nonintegral `xi*N_r` because Constraint (23)
  declares `g` integer.
- Solved values of every `g` variable match the Eq. (17) expression.
- Uniform `kappa=1` and `kappa=2` test environments solve optimally.

### Stage 9 — Per-node energy constraint

#### Scope and paper source

- Implemented Constraint (21) for every sensor `i in W`.
- Included transmitted and received data/control bits for self-generated and
  relayed traffic.
- Bounded each sensor expression by the common `epsilon` variable.

#### Decisions and verification

- The BS is excluded from Constraint (21), matching its `i in W` domain.
- Transmit energy uses the per-arc `E*_T,ij`; reception uses constant `E_R`.
- Tests inspect PuLP coefficients directly for outgoing data/control,
  incoming data, and the `-epsilon` term.

### Stage 10 — Bandwidth and interference constraint

#### Scope and paper source

- Implemented Constraint (22) for every `i in V`.
- Added own transmission, own reception, and Eq. (26)-selected blocked airtime.
- Used the Table I values `R_b`, `N_r`, and `t_r`.

#### Interpretation decision

The paper prints the interference-link domain as `A\\{i}` without formally
defining subtraction of a node from an arc set. It also describes this term as
bandwidth lost to neighboring transmissions, while own transmission and
reception already appear in the first two terms. The implementation therefore
interprets `A\\{i}` as arcs with neither endpoint equal to `i`. This avoids
double-counting incident traffic. The complete literal Eq. (26) indicators
remain available in `InterferenceEnvironment`, so this interpretation can be
changed locally if stronger source evidence is found.

#### Verification

- Tests inspect separate coefficients for own transmission, own reception, and
  one nonincident interfering arc.
- An incident arc marked true by literal Eq. (26) is charged once as own
  traffic, not again as interference.
- The complete two-sensor regression model contains 385 named constraints.
- Fixed `kappa=1` and `kappa=2` instances solve optimally with HiGHS.
- Full verification reports 69 passing tests; Ruff, IDE diagnostics, and
  `git diff --check` report no issues.

#### Review before Stage 11

- Confirm the `A\\{i}` nonincident-arc interpretation for Constraint (22).
- Confirm control traffic should continue requiring symmetric directed arcs.
- Stage 11 will extract paths, objective, node energy, and airtime diagnostics
  without changing the mathematical formulation.

### Stage 11 — Solution extraction

#### Scope and files

- Added `src/kcon_uwsn/solution.py` with an immutable, solver-independent
  `Solution` dataclass.
- Added extraction of status, `epsilon`, nonzero `f/g/h/p`, packet allocations,
  and ordered source-to-BS paths.
- Added independently evaluated per-node energy and airtime diagnostics.
- Added packet-balance, connectivity-shortfall, energy-violation, and
  airtime-violation diagnostics.
- Exported `Solution` and `extract_solution` from the package.
- Added 8 focused tests in `tests/test_solution.py`.

#### Paper sources

- Objective (6): objective energy `epsilon`.
- Constraint (8): generated-packet balance by source.
- Constraints (12)–(20): non-bifurcating, disjoint path reconstruction.
- Constraint (18): active path count versus required `kappa`.
- Constraint (21): per-sensor transmit/receive energy.
- Constraint (22) and Eq. (26): per-node airtime.

#### Decisions

- The result contains plain numbers and immutable mappings, not PuLP objects,
  so plotting and the later runner do not depend on solver internals.
- Models without an incumbent return a status-only solution instead of raising
  while reading undefined variable values.
- Decision-variable maps are sparse: only nonzero `f`, `g`, `p`, and active
  `h` values are retained.
- Path arcs are ordered by following the unique next hop from source to BS.
  Branches, cycles, and disconnected active arcs raise explicit errors because
  they would contradict the implemented path constraints.
- Energy and airtime are recomputed directly from extracted flows and
  environment coefficients. This independently checks Constraints (21)–(22)
  rather than trusting their stored solver slacks.
- Numerical extraction uses a configurable positive tolerance, defaulting to
  `1e-7`.

#### Verification

- An unsolved model produces `Not Solved` with no incumbent values.
- A solved `kappa=2` case returns contiguous, cycle-free source-to-BS paths.
- Every source has zero packet-balance error and zero connectivity shortfall.
- Maximum recomputed sensor energy agrees with `epsilon`.
- Recomputed node airtime satisfies Constraint (22).
- Extracted mappings reject mutation.
- Full verification reports 77 passing tests; Ruff, IDE diagnostics, and
  `git diff --check` report no issues.

#### Review before Stage 12

- Confirm the sparse solution representation and strict path validation.
- Confirm that status-only extraction is preferred over exceptions for models
  without an incumbent.
- Stage 12 will add CLI orchestration and solver options without altering the
  environment, formulation, or extraction calculations.

### Stage 12 — Runner

#### Scope and files

- Added `src/kcon_uwsn/run.py` with `solve_experiment`, `RunResult`, CLI
  argument parsing, summary reporting, and a Scenario-I workflow.
- Added the `kcon-uwsn` console script in `pyproject.toml`.
- Exposed deployment dimensions, partition counts, `xi`, seed, dimensionality,
  time limit, MIP gap, thread count, and solver selection.
- Retained HiGHS as the default and exposed bundled open-source CBC as a
  fallback.

#### Decisions

- `model.py` remains free of solver options; orchestration owns all HiGHS/CBC
  settings.
- Normal CLI defaults use a small four-sensor deployment. Paper-scale work
  requires the explicit `--figure-3` mode.
- Invalid time limits, gaps, thread counts, and solver names fail before model
  construction.
- A no-incumbent solve returns exit code 2 after printing status, rather than
  attempting to plot undefined values.
- Thread count defaults to the solver's existing process-global setting.
  Forcing a different count after an earlier HiGHS solve can return `Not
  Solved`; users may still set `--threads` in a fresh process.

#### Verification

- The wrapper completes environment → model → HiGHS → solution on a small
  deterministic case.
- CLI output reports status, wall time, `epsilon` in kJ, active path counts,
  and maximum energy/airtime residuals.
- Runner tests cover valid solves and invalid solver settings.
- Final verification reports 86 passing tests; Ruff, IDE diagnostics, and
  `git diff --check` report no issues.

### Stage 13 — Fig. 3(a) and Fig. 3(b)

#### Scope and files

- Added `src/kcon_uwsn/plotting.py`.
- Implemented topology and Scenario-I panel renderers.
- Added separate/combined PNG output and deterministic JSON metadata.
- Added data-level and deterministic-image tests in
  `tests/test_runner_plotting.py`.
- Generated final artifacts under `results/`:
  - `figure_3a_network_topology.png`
  - `figure_3b_scenario_i.png`
  - `figure_3ab_scenario_i.png`
  - `figure_3ab_metadata.json`

#### Paper sources and visual semantics

- Section IV-B and Fig. 3(a): 12 labeled sensors, BS at `(-0.5,0)`, equal
  1×1 km axes.
- Table III Scenario-I: all 12 sensors in `W_1` with `kappa_1=1`.
- Fig. 3(b): aggregate flow links, per-sensor energy colors, bottleneck source
  paths, and `epsilon`.

#### Reproducibility and tractability decisions

- Seed 42 fixes the generated topology. The paper's coordinates and seed are
  unavailable, so the images reproduce methodology and visual semantics rather
  than exact geometry.
- The default paper model continues to use Table I `N_l=5`.
- The figure workflow explicitly uses `N_l=2`. The paper's Scenario-I panel
  shows at most two active paths for the highlighted source, and reducing the
  path slots makes the open-source solve tractable. This deviation is embedded
  in `figure_3ab_metadata.json`.
- HiGHS found a feasible full-`N_l=5` incumbent near 23.774 kJ, but its Python
  binding aborted while returning the large model inside Cursor's sandbox.
  CBC returned cleanly but found no integer incumbent within 120 seconds.
  Running the `N_l=2` HiGHS workflow outside that sandbox completed normally.
- The no-incumbent discovery exposed a bug: CBC populated LP-relaxation
  variable values despite reporting no integer solution. Extraction now checks
  PuLP's incumbent status (`sol_status`) before reading any values.

#### Generated result

The documented figure command completed with:

- Status: Optimal under the configured 15% relative-gap criterion.
- Wall time: 6.673 s.
- `epsilon`: 23.771310 kJ.
- Nodes 1–10 used one active path; nodes 11–12 used two.
- Maximum energy and airtime violations: zero.

The generated metadata records positions, seed, connectivity, objective,
active-path counts, `N_l=2`, and both reproduction/deviation notes.

#### Review before Stage 14

- Confirm the visual encoding and explicit `N_l=2` figure-workflow deviation.
- Stage 14 should audit all paper references and reproducibility commands; it
  should not silently promote this figure setting to the default MILP.

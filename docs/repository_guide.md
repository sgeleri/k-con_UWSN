# Repository Guide

This document summarizes what `k-con_UWSN` does, how to run it, which options
are available, what files and console outputs are produced, and how to
interpret the current results under `results/`.

## What this repository does

`k-con_UWSN` is a paper-traceable Python implementation of:

> C. Tantur Karagul, M. B. Akgun, H. U. Yildiz, and B. Tavli,
> “Mitigating Energy Cost of Connection Reliability in UWSNs Through
> Non-uniform k-Connectivity,” IEEE Internet of Things Journal, 2025.

In short, the repository:

1. Builds an underwater wireless sensor network (UWSN) environment.
2. Formulates the paper’s mixed-integer linear program (MILP).
3. Solves it with an open-source solver (HiGHS by default, CBC as fallback).
4. Extracts routing/energy/airtime diagnostics from the solver solution.
5. Optionally generates Section IV-B Scenario-I topology and energy figures.

The MILP minimizes the maximum sensor energy consumption, denoted `ε`
(epsilon), while enforcing non-uniform `k`-connectivity: each sensor source
must have `κ` node-disjoint paths to the base station (BS).

### Main code modules

| Module | Role |
| --- | --- |
| `src/kcon_uwsn/params.py` | Paper constants from Tables I–II and experiment settings |
| `src/kcon_uwsn/environment.py` | Deployment, distances, arcs, acoustic energy, interference, connectivity partitions |
| `src/kcon_uwsn/model.py` | PuLP MILP: Objective (6) and Constraints (7)–(25) |
| `src/kcon_uwsn/solution.py` | Solver-independent extraction, path reconstruction, diagnostics |
| `src/kcon_uwsn/run.py` | CLI and experiment/figure orchestration |
| `src/kcon_uwsn/plotting.py` | Topology and Scenario-I figure rendering |

Supporting documents:

- `plan.md` — staged development plan
- `implementation_process.md` — chronological decisions and verification
- `docs/paper_traceability.md` — code ↔ paper equation/table/figure mapping
- `docs/fidelity_audit.md` — Stage 14 fidelity and reproducibility audit
- `docs/error_resolve.md` — runtime/solver bug fixes

### Current scope and non-goals

Implemented:

- Full environment preprocessing and the complete MILP formulation
- Small custom experiments through the CLI
- Scenario-I (Table III) figure workflows for Fig. 3(a)/(b)-style outputs

Not implemented in v1:

- Table III Scenarios II–VII as automated experiments
- Table IV’s eleven configurations and 20-topology averaging
- Fig. 3(c)–(i) and Section IV-D survival analysis
- Exact pixel/numerical reproduction of the paper’s unpublished topology

## How to install and run

### Setup

```shell
python -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock.txt -e ".[dev]"
```

Verify:

```shell
pytest
ruff check .
ruff format --check .
kcon-uwsn --help
```

### End-to-end pipeline of one run

Every solve follows the same sequence:

1. Create `ExperimentParameters` (sensor count, volume, connectivity counts, seed, `ξ`).
2. Build `EnvironmentData`:
   - random uniform deployment (BS at a top corner),
   - directed acoustic arcs,
   - transmission/reception energies,
   - connectivity partition (`W_1`, `W_2`, `W_3`),
   - interference indicators from Eq. (26).
3. Build the PuLP model and solve with HiGHS or CBC.
4. Extract a `Solution` object:
   - status and termination reason,
   - objective `ε`,
   - active paths,
   - per-node energy and airtime,
   - residual diagnostics.
5. For figure workflows only, write PNG panels plus JSON metadata.

## Run selections

There are three run modes.

### 1. Custom small experiment (default)

Use this for quick model checks and parameter experiments.

```shell
kcon-uwsn \
  --sensors 4 \
  --volume-km 0.2 0.2 0.1 \
  --connectivity-counts 4 0 0 \
  --two-dimensional \
  --time-limit 30 \
  --mip-gap 0
```

This mode prints a console summary and does not write figure files.

### 2. Paper-model Scenario-I figure workflow

```shell
kcon-uwsn --figure-3 --seed 42 --output-dir results
```

Defaults for this mode:

| Setting | Value |
| --- | --- |
| Sensors | 12 |
| Volume | 1×1×0.30 km (2D cross-section) |
| Connectivity | Scenario-I: all sensors in `W_1` (`κ=1`) |
| Maximum paths `N_l` | 5 (Table I) |
| Requested MIP gap | 1% |
| Default time limit | 60 s |
| Default threads | 1 |
| Default solver | HiGHS |

This is the paper-faithful path-slot setting. With open-source solvers it may
hit the time limit and return only a feasible incumbent.

### 3. Approximate Scenario-I figure workflow

```shell
kcon-uwsn --approximate-figure-3 --seed 42 --output-dir results
```

Defaults for this mode:

| Setting | Value |
| --- | --- |
| Sensors / volume / Scenario-I | Same as paper-model figure mode |
| Maximum paths `N_l` | 2 (tractable approximation) |
| Requested MIP gap | 15% |
| Default time limit | 45 s |
| Default threads | 1 |
| Default solver | HiGHS |

Filenames and metadata explicitly label this as an approximation. Prefer this
mode for a fast, reproducible end-to-end figure run.

### CLI options

| Option | Meaning | Notes |
| --- | --- | --- |
| `--sensors` | Number of sensor nodes | Default `4` for custom runs |
| `--volume-km DX DY DZ` | Deployment volume in kilometers | Converted to meters internally |
| `--connectivity-counts N1 N2 N3` | Cardinalities `|W_1|`, `|W_2|`, `|W_3|` | Defaults to all sensors in `W_1` |
| `--xi` | Control-to-data frequency `ξ` | Default `1.0` |
| `--seed` | Random seed | Affects deployment; assignment uses an independent derived stream |
| `--two-dimensional` | Force `z=0` for all sensors | Used by both figure workflows |
| `--time-limit` | Solver wall-clock limit (seconds) | Must be positive |
| `--mip-gap` | Requested relative MIP gap | Must satisfy `0 <= gap < 1` |
| `--threads` | Solver threads | Figure modes default to `1` |
| `--solver {highs,cbc}` | Backend solver | Default `highs` |
| `--solver-log` | Print native solver log | Off by default |
| `--figure-3` | Paper-model figure workflow | Mutually exclusive with approximate mode |
| `--approximate-figure-3` | Tractable `N_l=2` figure workflow | Mutually exclusive with paper-model mode |
| `--output-dir` | Directory for figure artifacts | Default `results` |

### Exit codes

| Exit code | Meaning |
| --- | --- |
| `0` | Optimal, or optimal within the requested solver tolerance |
| `2` | No valid incumbent solution |
| `3` | Feasible incumbent whose global optimality is unproven |

## What each run outputs

### Console summary (all modes)

Every successful solve prints:

- `Status` — high-level interpretation (`Optimal`, `Optimal within solver tolerance`, `Feasible`, `No Solution`, …)
- `Termination` — backend termination reason (`Optimal`, `Time limit reached`, …)
- `Wall time` — measured end-to-end solve time
- `epsilon` — objective maximum sensor energy in kJ
- `Relative MIP gap` — when available from the solver
- `Active paths` — number of reconstructed source-to-BS paths per sensor
- `Maximum residuals` — recomputed energy and airtime constraint violations

Figure modes also print the written file paths.

### Figure artifacts

#### Paper-model (`--figure-3`)

| File | Content |
| --- | --- |
| `figure_3a_network_topology.png` | Labeled 12-sensor topology with BS marker |
| `figure_3b_scenario_i.png` | Energy-colored sensors, flows, bottleneck paths, `ε` |
| `figure_3ab_scenario_i.png` | Side-by-side panels (a) and (b) |
| `figure_3ab_metadata.json` | Full reproducibility record |

#### Approximate (`--approximate-figure-3`)

| File | Content |
| --- | --- |
| `approximate_figure_3a_topology.png` | Same visual semantics as Fig. 3(a) |
| `approximate_figure_3b_scenario_i.png` | Same visual semantics as Fig. 3(b) |
| `approximate_figure_3ab_scenario_i.png` | Combined approximate panels |
| `approximate_figure_3ab_metadata.json` | Full reproducibility record, including the `N_l=2` deviation |

### How to read the PNGs

**Panel (a) / topology**

- Red star: base station at `(-0.5, 0)` km for the 1×1 km Scenario-I area
- Blue markers: sensor nodes 1–12
- Axes are equal and reported in kilometers

**Panel (b) / Scenario-I solution**

- Marker color: per-sensor energy in kJ
- Faint gray lines: individual data-flow arcs
- Dashed thicker lines: aggregate relay traffic incident to the bottleneck node
- Colored solid lines: reconstructed active paths of the bottleneck source
- Title reports bottleneck node ID, `ε`, and the MIP gap when nonzero

### How to read the JSON metadata

Important fields:

| Field | Meaning |
| --- | --- |
| `artifact_kind` | `paper-model-methodological-reproduction` or `explicit-n_l-2-approximation` |
| `paper_reference` | Paper claim level for the artifact |
| `model_deviation` | Explicit `N_l` deviation note, if any |
| `random_seed` | Seed used for the topology |
| `positions_m` | Full node coordinates in meters (BS first, then sensors) |
| `connectivity_counts` | `|W_1|`, `|W_2|`, `|W_3|` |
| `maximum_paths` | Path slots `N_l` used in the model |
| `status` / `termination_reason` | Interpreted result and solver stop reason |
| `epsilon_j` | Objective value in joules (`/1000` for kJ) |
| `best_bound_j` | Best dual bound, when available |
| `relative_gap` | Achieved relative MIP gap |
| `active_path_count_by_source` | Number of reconstructed paths per sensor |
| `run_configuration` | Solver name, time limit, requested gap, threads, wall time |
| `software_versions` | Python and package versions |
| `artifact_sha256` | Hashes of the three PNG files |

## Detailed explanation of current results

The current `results/` directory contains both workflows for seed `42` on the
same synthetic 12-sensor Scenario-I topology. Because the paper does not publish
its original coordinates or seed, these are methodological reproductions, not
exact numerical replicas of the published figures.

### Shared topology (both workflows)

- 12 sensors + 1 BS
- Volume: 1.0 × 1.0 × 0.30 km, forced 2D (`z = 0`)
- Scenario-I connectivity: `(12, 0, 0)` → every sensor has `κ = 1`
- Seed: `42`
- BS position: `(-500, 0, 0)` m = `(-0.5, 0)` km

The topology PNG therefore looks the same for both workflows; only the
routing/energy solution can differ.

### Approximate result (`N_l = 2`)

Files:

- `approximate_figure_3a_topology.png`
- `approximate_figure_3b_scenario_i.png`
- `approximate_figure_3ab_scenario_i.png`
- `approximate_figure_3ab_metadata.json`

Solved configuration:

| Quantity | Value |
| --- | --- |
| Artifact kind | explicit `N_l=2` approximation |
| Solver | HiGHS |
| Threads | 1 |
| Time limit | 45 s |
| Wall time | about 6.8 s |
| Requested MIP gap | 15% |
| Achieved relative gap | 11.40% |
| Status | Optimal within solver tolerance |
| Termination | Optimal |
| `ε` | 23.771310 kJ |
| Best bound | 21.061423 kJ |

Path counts:

- Sensors 1–10: 1 active path each
- Sensors 11–12: 2 active paths each

Interpretation:

- The model only allows at most two path slots per source.
- The solver stopped after proving the incumbent is within the requested 15%
  tolerance; the achieved gap is about 11.4%.
- Nodes 11 and 12 use both available path slots even though Scenario-I only
  requires `κ=1`. Extra paths can appear because the formulation may still
  activate unused slots when they do not worsen the bottleneck objective.
- This result is faster and intentionally approximate. It must not be treated as
  the Table I paper model.

### Paper-model result (`N_l = 5`)

Files:

- `figure_3a_network_topology.png`
- `figure_3b_scenario_i.png`
- `figure_3ab_scenario_i.png`
- `figure_3ab_metadata.json`

Solved configuration:

| Quantity | Value |
| --- | --- |
| Artifact kind | paper-model methodological reproduction |
| Solver | HiGHS |
| Threads | 1 |
| Time limit | 60 s |
| Wall time | about 61.6 s |
| Requested MIP gap | 1% |
| Achieved relative gap | 11.41% |
| Status | Feasible |
| Termination | Time limit reached |
| `ε` | 23.773617 kJ |
| Best bound | 21.061423 kJ |
| Model deviation | none (`N_l=5`) |

Path counts:

- Most sensors: 1 active path
- Sensor 7: 3 active paths

Interpretation:

- This uses the paper’s Table I path-slot count (`N_l=5`).
- The solver found a feasible incumbent but did **not** prove optimality to the
  requested 1% gap before the time limit. Exit code for such a run is `3`.
- The objective is essentially the same order as the approximate run
  (~23.77 kJ), which is expected on the same unpublished synthetic topology.
- Sensor 7 is the multi-path / bottleneck-related source in this incumbent; the
  figure panel highlights the bottleneck node’s paths and energy colors.
- Because the gap remains about 11%, this incumbent is not a proven global
  optimum under the requested tolerance.

### Why these `ε` values differ from the paper’s 10.40 kJ

The paper reports Scenario-I `ε = 10.40 kJ` on its own unpublished 12-sensor
deployment. This repository cannot recreate that exact instance. Differences
arise from:

1. Different sensor coordinates and random seed
2. Open-source solver limits and remaining MIP gap
3. In the approximate workflow, the reduced path space `N_l=2`

Therefore:

- Approximate artifacts demonstrate a tractable, labeled reproduction workflow.
- Paper-model artifacts demonstrate the Table I formulation on a deterministic
  synthetic instance.
- Neither claim exact numerical agreement with the published figure values.

### Small-model sanity check (no figure files)

A typical custom run used during verification:

```shell
kcon-uwsn \
  --sensors 4 \
  --volume-km 0.2 0.2 0.1 \
  --connectivity-counts 4 0 0 \
  --two-dimensional \
  --time-limit 30 \
  --mip-gap 0
```

Expected style of result:

- Status: `Optimal`
- `ε` around `1.46 kJ` for this small instance
- One active path per sensor under Scenario-I-like `κ=1`
- Near-zero energy and airtime residuals

This confirms the solver pipeline works before running the 12-sensor figure
cases.

## Practical recommendations

1. For a quick verified figure generation, use `--approximate-figure-3`.
2. For the paper’s `N_l=5` model, use `--figure-3` and expect longer runtimes;
   raise `--time-limit` if you need a better gap.
3. Always inspect both `Status` and `Termination`, not just the objective.
4. Use the JSON metadata (especially `artifact_kind`, `maximum_paths`,
   `relative_gap`, and `epsilon_j`) when comparing runs.
5. Do not compare synthetic `ε` values directly against the paper’s published
   10.40 kJ as a fidelity pass/fail metric.

## Related documents

- Setup and short examples: [`README.md`](../README.md)
- Paper mapping: [`paper_traceability.md`](paper_traceability.md)
- Audit conclusions: [`fidelity_audit.md`](fidelity_audit.md)
- Bug fixes that restored solver feasibility: [`error_resolve.md`](error_resolve.md)
- Chronological implementation log: [`../implementation_process.md`](../implementation_process.md)

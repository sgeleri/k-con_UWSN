# Tantur 2025 Implementation Plan

## Goal

Build a paper-traceable implementation of Tantur et al. (2025), using PuLP
with the open-source HiGHS solver. Work proceeds one reviewed stage at a time:
parameters and environment first, MILP constraints in logical groups, the
runner last, and finally Section IV-B Fig. 3(a) and Fig. 3(b).

The target figures are:

- **Fig. 3(a), Network Topology:** BS at `(-0.5, 0)` and 12 sensors in the
  1×1 km two-dimensional deployment.
- **Fig. 3(b), Scenario-I:** all sensors assigned `κ_1=1` per Table III,
  showing optimized packet-flow links and per-node energy dissipation.

The paper does not publish the 12 numerical sensor coordinates or random seed.
The output will therefore be a deterministic, methodologically faithful
reproduction—not a claim of pixel-identical or numerically identical results.

## Working method

For each stage:

1. Review the exact paper passage and equations.
2. Implement only that stage.
3. Add focused tests tied to the same paper references.
4. Update `implementation_process.md` and `docs/paper_traceability.md`.
5. Present code, decisions, assumptions, and test results for review.
6. Continue only after approval.

## Architecture

```text
k-con_UWSN/
  pyproject.toml
  implementation_process.md
  docs/paper_traceability.md
  src/kcon_uwsn/
    params.py
    environment.py
    model.py
    run.py
    plotting.py
  tests/
  results/
```

- `params.py`: paper constants and experiment settings.
- `environment.py`: geometry and precomputed coefficients; no solver imports.
- `model.py`: PuLP variables, objective, and constraints; no geometry.
- `run.py`: HiGHS configuration and orchestration, implemented last.
- `plotting.py`: Fig. 3(a)/(b) rendering from environment and solution data.
- BS index is `0` in code; the paper's BS index is `1`.
- Gurobi is deferred so the one-year academic license remains available later.

## Traceability standard

Direct implementations use a nearby comment such as:

```python
# Paper: Section III-B, Eq. (5), Table II.
# Select the lowest transmission-power level covering distance d_ij.
```

Comments cite the most specific section, equation, table, or figure. Paper
behavior is distinguished from implementation choices such as zero-based
indexing, sparse storage, seeds, and solver options. Python docstrings retain
the paper symbols alongside implementation names. Corresponding tests carry
the same references.

## Stages

### Stage 0 — Scaffolding

Create packaging, source/test directories, `implementation_process.md`, and
`docs/paper_traceability.md`. Verify imports and the test harness.

### Stage 1 — Parameters and notation

Implement frozen parameter dataclasses:

- Section III-A and Table I network/traffic values.
- Section III-B and Table I acoustic values.
- Table II power levels and ranges.
- Validation for ranges, partitions, and `κ ≤ N_l`.

Store energy internally in J/bit and test all literals and unit conversions.

### Stage 2 — Network environment

Implement the Section III-A deployment:

- Reproducible uniform sensor placement and static corner sonobuoy.
- Pairwise distances in meters.
- Directed sets `V`, `W`, and `A`, where `d_ij ≤ R_max(ℓ_max)`.
- Fig. 1 is used only for the 3D deployment concept.

Test hand-placed nodes, arc directions, self-loop exclusion, range boundaries,
and disconnected nodes.

### Stage 3 — Acoustic energy environment

Implement:

- Transmission loss from Eq. (1).
- Absorption coefficient from Eq. (2).
- Transmit and receive energy from Eqs. (3)–(4).
- Per-link minimum power selection from Eq. (5).
- Numerical validation against Table II.

Test every range boundary and J/mJ conversion.

### Stage 4 — Connectivity and interference environment

Implement:

- Disjoint `W_n` partitions and node-to-`κ_n` mapping, based on Section III-A,
  Constraint (18), and Tables III–IV.
- Explicit node sets and seeded cardinality-based assignment.
- Sparse interference indicator `I^i_jm` from Eq. (26).
- Immutable `EnvironmentData`.

Complete and review the environment before adding PuLP.

### Stage 5 — Variables, domains, and objective

Define `f`, `g`, `h`, `p`, and `ε` from Section III-C, apply Constraints
(23)–(25), and minimize `ε` per Objective (6). Test variable indices,
categories, bounds, and the objective without solving.

### Stage 6 — Flow construction

Add separate, equation-named helpers for:

- Flow conservation, Constraint (7).
- Generated traffic, Constraint (8).
- No re-entry to source, Constraint (9).
- Flow/use coupling, Constraints (10)–(11).
- No bifurcation, Constraint (12).

Demonstrate one tiny source-to-BS flow before proceeding.

### Stage 7 — Path structure and disjointness

Add:

- Link disjointness, Constraint (13).
- Path ordering, Constraint (14).
- Phantom-flow elimination, Constraints (15)–(16).
- Node disjointness, Constraints (19)–(20).

Test invalid shared-link, shared-relay, bifurcated, and phantom-flow cases.

### Stage 8 — Control traffic and non-uniform connectivity

Add control traffic from Constraint (17) and non-uniform connectivity from
Constraint (18). Test uniform/mixed `κ`, all paper `ξ` values, and infeasible
topologies with insufficient disjoint paths.

### Stage 9 — Energy constraint

Implement Constraint (21), including data/control transmission, reception,
relaying, and the per-sensor `ε` bound. Compare a tiny route against a manual
energy calculation.

### Stage 10 — Bandwidth and interference

Implement Constraint (22) using Eq. (26): own transmission, reception, and
blocked airtime, bounded by `N_r t_r` for every node in `V`. Test each term
independently and an interference-only infeasible case.

### Stage 11 — Solution extraction

Create a solver-independent result containing status, `ε`, nonzero variables,
packet allocations, reconstructed paths, and per-node energy/airtime
diagnostics. Validate path counts and constraint residuals.

### Stage 12 — Runner

Implement the CLI last:

1. Parse deployment, partition, `ξ`, seed, time limit, and MIP gap.
2. Build parameters and environment.
3. Build the PuLP model.
4. Solve with `pulp.HiGHS`.
5. Report status, `ε` in kJ, runtime, paths, and diagnostics.

Use a small deterministic default; paper-scale cases require explicit options.

### Stage 13 — Fig. 3(a) and Fig. 3(b)

Implement `plotting.py`:

- Render the deterministic 12-sensor topology with IDs, BS star, equal axes,
  kilometer units, and 1×1 km bounds.
- Solve Table III Scenario-I (`κ_1=1`, `W_1={1,...,12}`).
- Render active data-flow arcs, node energy colors, and bottleneck `ε`.
- Save separate and combined deterministic images under `results/`.
- Document that unpublished coordinates prevent exact figure reconstruction.

Use data-level tests rather than fragile pixel comparisons.

### Stage 14 — Fidelity audit

- Account for every implemented equation (1)–(26).
- Audit references to Tables I–IV and Figs. 1/3.
- Verify the complete chronological implementation log.
- Regenerate Fig. 3(a)/(b) from one documented command.
- Run formatting, linting, and all tests.

## v1 boundaries

- Implement the complete environment and MILP, but not all 20-topology Table IV
  experiments.
- Section IV-D survival analysis, Fig. 3(c)–(i), and Gurobi migration remain
  later work.
- Correctness and traceability take priority over 30-node HiGHS performance.

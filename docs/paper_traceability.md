# Paper Traceability

This matrix links implementation artifacts to:

> C. Tantur Karagul, M. B. Akgun, H. U. Yildiz, and B. Tavli,
> “Mitigating Energy Cost of Connection Reliability in UWSNs Through
> Non-uniform k-Connectivity,” IEEE Internet of Things Journal, 2025.

Paper-defined behavior and implementation-specific decisions are identified
separately. The matrix is updated after each reviewed implementation stage.

## Stage 1 — Parameters and notation

- `NetworkParameters`
  - Source: Section III-A and Table I.
  - Symbols: `N_r`, `t_r`, `s_k`, `l_d`, `l_c`, `R_b`, `N_l`, `M`, `γ`,
    `ξ`, and `κ_n`.
  - Test: `test_network_parameters_match_table_i`.
- `AcousticParameters`
  - Source: Section III-B, Eqs. (1)–(4), and Table I.
  - Symbols: `f_0`, `k_s`, `P_0`, and `P_r`.
  - Test: `test_acoustic_parameters_match_table_i`.
- `PowerLevelTable`
  - Source: Section III-B, Eq. (5), and Table II.
  - Symbols: `P_l`, `R_max(l)`, and `E_T(l)`.
  - Tests: `test_power_levels_match_table_ii` and
    `test_table_ii_energy_is_converted_to_joules_per_bit`.
- `ExperimentParameters`
  - Source: Section III-A, Fig. 1, Table I, and Tables III–IV.
  - Symbols: `(d_x, d_y, d_z)`, `|W|`, `ξ`, and
    `(|W_1|, |W_2|, |W_3|)`.
  - Tests: `test_default_experiment_matches_figure_1_scale` and partition
    validation tests.

## Stage 2 — Network environment

- `Deployment` and `generate_uniform_deployment`
  - Source: Section III-A and Fig. 1.
  - Symbols: `V`, `W`, `d_x`, `d_y`, and `d_z`.
  - Tests: reproducibility, corner BS, prism bounds, 2D cross section, and
    immutable position tests in `test_environment.py`.
- `pairwise_distances`
  - Source: Section III-A and Table I.
  - Symbol: `d_ij`.
  - Test: `test_pairwise_distances_are_euclidean_symmetric_and_zero_diagonal`.
- `build_directed_arcs`
  - Source: Section III-A graph definition.
  - Symbols: `A` and `R_max(l_max)`.
  - Test:
    `test_directed_arcs_include_range_boundary_and_exclude_self_loops`.
- `NetworkEnvironment` and `build_network_environment`
  - Source: Section III-A definition `G=(V,A)`.
  - Tests: graph-set, arc-consistency, and immutable-distance tests.
- `build_paper_network_environment`
  - Source: Section III-A and Table II.
  - Test: `test_paper_network_uses_table_ii_maximum_range`.

## Stage 3 — Acoustic energy environment

- `absorption_coefficient_db_per_km`
  - Source: Section III-B, Eq. (2).
  - Symbol: `alpha(f_0)`.
  - Test: `test_absorption_coefficient_matches_equation_2`.
- `frequency_component` and `transmission_loss`
  - Source: Section III-B, Eq. (1) and its following definition.
  - Symbols: `nu` and `TL(R_max(l))`.
  - Tests: frequency-component and transmission-loss equation tests.
- `transmission_energy_j_per_bit` and
  `power_level_energies_j_per_bit`
  - Source: Section III-B, Eq. (3), and Table II.
  - Symbol: `E_T(l)`.
  - Tests: Eq. (3) and all-power-level Table II comparison tests.
- `minimum_link_transmission_energy_j_per_bit`
  - Source: Section III-B, Eq. (5).
  - Symbol: `E*_T,ij`.
  - Tests: all range-boundary cases and the beyond-range infinity case.
- `AcousticEnergyEnvironment` and `build_acoustic_energy_environment`
  - Source: Section III-B, Eqs. (1)–(5).
  - Symbols: `E*_T,ij` and `E_R`.
  - Tests: per-arc power selection, Eq. (4) reception cost, and immutable
    coefficient mapping.

## Stage 4 — Connectivity and interference

- `ConnectivityPartition`, `build_explicit_connectivity_partition`, and
  `build_seeded_connectivity_partition`
  - Source: Section III-A, Constraint (18), Tables III–IV, and Section IV-C.
  - Symbols: `W_n`, `kappa_n`, and `S_P`.
  - Tests: explicit partition, disjointness/coverage, reproducibility, and
    cardinality tests in `test_connectivity_interference.py`.
- `InterferenceEnvironment` and `build_interference_environment`
  - Source: Section III-C, Eq. (26).
  - Symbol: `I^i_jm`.
  - Tests: exact true/false branches and sparse all-node mapping tests.
- `EnvironmentData` and `build_environment`
  - Source: Sections III-A–III-C through Eq. (26).
  - Test: complete explicit Table III-style environment construction.

## Stage 5 — MILP variables, domains, and objective

- `ModelVars` and `build_model`
  - Source: Section III-C variable definitions, Objective (6), and Constraints
    (23)–(25).
  - Symbols: `f^kl_ij`, `g^kl_ij`, `h^kl_ij`, `p^l_k`, and `epsilon`.
  - Tests: index counts, one-based path indices, variable domains, immutable
    maps, and objective structure in `test_model_stage_5.py`.

## Stage 6 — Flow construction

- `_add_constraint_07_flow_conservation`
  - Source: Section III-C, Constraint (7).
  - Test: solved source/BS/relay residual checks.
- `_add_constraint_08_generated_packets`
  - Source: Section III-C, Constraint (8).
  - Test: each source delivers `s_k*N_r=1440` packets.
- `_add_constraint_09_no_source_reentry`
  - Source: Section III-C, Constraint (9).
- `_add_constraints_10_11_flow_use_coupling`
  - Source: Section III-C, Constraints (10)–(11).
- `_add_constraint_12_single_next_hop`
  - Source: Section III-C, Constraint (12).

## Stage 7 — Path structure and disjointness

- `_add_constraint_13_link_disjointness`
  - Source: Section III-C, Constraint (13).
- `_add_constraint_14_monotone_path_index`
  - Source: Section III-C, Constraint (14).
- `_add_constraints_15_16_phantom_flow`
  - Source: Section III-C, Constraints (15)–(16).
- `_add_constraints_19_20_node_disjointness`
  - Source: Section III-C, Constraints (19)–(20).
- Tests: a solved `kappa=2` topology verifies separate path starts and that
  each relay is used by at most one path.

## Stage 8 — Control traffic and non-uniform connectivity

- `_add_constraint_17_control_flow`
  - Source: Section III-C, Constraint (17).
  - Test: every solved `g^kl_ij` equals
    `xi*N_r*(h^kl_ij+h^kl_ji)`.
- `_add_constraint_18_non_uniform_connectivity`
  - Source: Section III-C, Constraint (18).
  - Tests: uniform `kappa=1` and `kappa=2` solved topologies.

## Stage 9 — Per-node energy

- `_add_constraint_21_energy`
  - Source: Section III-C, Constraint (21).
  - Test: transmission/reception data and control coefficients are checked
    directly against `E*_T,ij`, `E_R`, `l_d`, and `l_c`.

## Stage 10 — Bandwidth and interference

- `_add_constraint_22_bandwidth`
  - Source: Section III-C, Constraint (22), using Eq. (26).
  - Test: own transmission, own reception, and nonincident interfering-link
    coefficients are checked independently.
- Full formulation regression
  - Test: the two-sensor complete graph has 385 named constraints and solves
    optimally with HiGHS.

## Stage 11 — Solution extraction

- `Solution` and `extract_solution`
  - Source: Objective (6) and Constraints (8), (12)–(22).
  - Outputs: solver status, `epsilon`, nonzero `f/g/h/p`, ordered paths,
    per-node energy, per-node airtime, path counts, and residual diagnostics.
  - Tests: status-only extraction, sparse values, contiguous source-to-BS
    paths, packet balance, `kappa` satisfaction, energy/objective agreement,
    airtime feasibility, and immutable results in `test_solution.py`.
- `_node_energy`
  - Source: Constraint (21).
- `_node_airtime`
  - Source: Constraint (22) and Eq. (26), with the documented `A\\{i}`
    interpretation.

## Stage 12 — Runner

- `solve_experiment`
  - Source flow: build Sections III-A/B environment, build Section III-C MILP,
    solve, and extract Stage 11 diagnostics.
  - Solver: PuLP HiGHS by default; open-source CBC is selectable as a fallback.
- `scenario_i_experiment`
  - Source: Section IV-B and Table III Scenario-I.
  - Values: 12 sensors, 1×1 km 2D cross section, `xi=1`,
    `(|W_1|,|W_2|,|W_3|)=(12,0,0)`.
- CLI
  - Inputs: deployment, connectivity cardinalities, `xi`, seed, solver,
    time limit, relative MIP gap, and threads.
  - Tests: complete small solve, invalid options, Scenario-I configuration,
    and CLI output in `test_runner_plotting.py`.

## Stage 13 — Fig. 3(a) and Fig. 3(b)

- `plot_network_topology`
  - Source: Section IV-B, Fig. 3(a).
  - Output semantics: 12 labeled sensors, corner BS star, equal 1×1 km axes.
- `plot_scenario_i`
  - Source: Section IV-B, Fig. 3(b), and Table III Scenario-I.
  - Output semantics: aggregate data-flow links, sensor energy colors,
    bottleneck paths, and `epsilon`.
- `save_figure_3_outputs`
  - Outputs: separate panels, combined panel, and deterministic JSON metadata.
  - Tests: artifact/data checks and deterministic topology-image hash.

## Implementation-specific decisions

- Code stores transmission energy in J/bit. Table II reference values are
  retained in mJ/bit and explicitly converted.
- Parameter dataclasses are immutable so a run cannot change paper constants.
- The default experiment uses the 30-sensor, 1×3×0.30 km deployment illustrated
  by Fig. 1 and `ξ=1`, which Section IV-A uses after its frequency comparison.
- `connectivity_counts` records cardinalities only. Explicit `W_n` membership
  belongs to the Stage 4 environment implementation.
- Validation limits `ξ` and `κ_n` to the ranges analyzed in Table I. Supporting
  extrapolation beyond those ranges would require an explicit later decision.
- Coordinates use meters with `x∈[-d_x/2,d_x/2]`, `y∈[0,d_y]`, and
  `z∈[-d_z,0]`; the BS is at `(-d_x/2,0,0)`. The paper specifies a top corner
  but does not prescribe a coordinate origin.
- Nodes are zero-based with the BS at index 0. This differs from the MILP
  equations' BS index 1 and is documented in code.
- The arc comparison is inclusive (`d_ij≤R_max(l_max)`) and creates both
  directed arcs when a symmetric acoustic range connects two nodes.
- Equations (1)–(3), rather than the rounded Table II values, are authoritative
  for generated transmission energies. Calculated values are compared to Table
  II within 0.001 mJ/bit (one unit of its last published decimal place).
- Direct calculation gives 9.567450 mJ/bit for level 9 while Table II prints
  9.568 mJ/bit. This small discrepancy is recorded rather than hidden by
  altering the published equations.
- Per-arc transmission energies are stored as an immutable mapping keyed by
  exactly the directed arc set `A`; all MILP-facing energies use J/bit.
- Cardinality-based `W_n` assignment uses a seeded NumPy permutation because
  Section IV-C specifies random assignment but does not publish seeds.
- Eq. (26) is evaluated literally for every `i in V` and `(j,m) in A`.
  Consequently, the indicator is also one at transmitter `i=j`; the later
  Constraint (22) implementation will separately define its summation domain.
- Only true Eq. (26) indicators are stored, grouped by node, while
  `InterferenceEnvironment.indicator` provides the complete zero/one view.
- PuLP variables use one-based path indices to match the paper while retaining
  zero-based node indices from the environment.
- PuLP 3.3's current `problem.add_variable` API is used. Variables not yet used
  by an objective or constraint are exposed through `ModelVars` and are
  registered by PuLP lazily as later constraint stages reference them.
- Every constraint name begins with its paper equation number (`c07` through
  `c22`) to support LP inspection and equation-level diagnostics.
- Constraint (17) checks that `xi*N_r` is integral because `g` is declared
  integer in Constraint (23).
- Constraint (22)'s printed `A\\{i}` domain is interpreted as arcs not incident
  to node `i`. Own incident arcs are already charged by the transmission and
  reception terms, so this prevents duplicate airtime accounting.
- Solution extraction returns a status-only object when no incumbent exists,
  allowing the later runner to report unsolved/infeasible models without
  reading undefined PuLP values.
- Only nonzero decision values are retained. Active arcs are ordered from each
  source to the BS and extraction fails loudly if a solved arc set branches,
  cycles, or contains disconnected components.
- Energy and airtime diagnostics are recomputed independently from extracted
  values rather than copied from constraint slacks.
- The normal runner retains Table I `N_l=5`. The Fig. 3 workflow uses `N_l=2`
  as an explicit open-source-solver tractability setting; the paper's
  Scenario-I illustration itself shows no source requiring more than two active
  paths. This deviation is written into the generated metadata.
- Figure output is a methodological reproduction because the paper does not
  publish its 12 sensor coordinates or seed.
- HiGHS remains the default solver. CBC is exposed as an open-source fallback,
  but it did not find a 12-sensor integer incumbent within the tested
  120-second limit.

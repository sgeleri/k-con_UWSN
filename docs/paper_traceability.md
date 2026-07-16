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

# Stage 14 Fidelity Audit

## Conclusion

All numbered equations (1)–(26) are represented. No direct transcription
error was found in Eqs. (1)–(21) or (23)–(26), and Tables I–II are faithfully
encoded. Constraint (22) remains interpretation-dependent because the paper
does not formally define its printed `A\{i}` domain.

The project produces a traceable implementation of the environment and MILP.
Its versioned Scenario-I figures are explicitly labeled approximations rather
than exact reproductions of Fig. 3.

## Equation inventory

- Eqs. (1)–(5): acoustic propagation and energy preprocessing in
  `environment.py`.
- Objective (6): minimization of maximum sensor energy in `model.py`.
- Constraints (7)–(20): flow, path, connectivity, and disjointness rules in
  `model.py`.
- Constraints (21)–(22): energy and airtime/interference limits in `model.py`.
- Domains (23)–(25): integer and binary decision-variable domains.
- Eq. (26): sparse interference indicators in `environment.py`.

Constraint (22) is implemented with `A\{i}` interpreted as arcs not incident
to node `i`, preventing own transmission/reception airtime from being counted
again as interference. The prose supports this choice, but author confirmation
or sensitivity analysis is still required.

## Corrections made during the audit

- Solver termination, incumbent status, best bound, and relative gap are stored
  separately. A time-limited incumbent is reported as feasible, and a
  gap-terminated result is reported as optimal only within solver tolerance.
- CLI exit codes distinguish optimal (`0`), no valid incumbent (`2`), and
  feasible-but-unproven (`3`) results.
- Extraction validates integrality and constraints before reading a solver
  incumbent. Disconnected/cyclic arcs permitted by the formulation are reported
  as `extraneous_arcs` instead of causing path reconstruction to fail.
- The paper-model `--figure-3` workflow now uses Table I `N_l=5` and a 1%
  requested gap. The tractable `N_l=2`, 15%-gap workflow moved to
  `--approximate-figure-3`; filenames, plot text, and metadata identify it as an
  approximation.
- Fig. 3(b)-style rendering now separates faint individual flows from aggregate
  bottleneck-incident relay traffic.
- Deployment and connectivity assignment use independent deterministic random
  streams.
- Strict Figure-3 configuration validation, dependency locking, explicit
  thread configuration, software/solver metadata, and PNG hashes were added.
- Canonical approximate outputs are versionable under `results/`.

## Reproducibility and tests

The regular verification suite reports 94 passed tests and one skipped
opt-in paper-scale test. The full 12-sensor approximate workflow passes when
enabled with `RUN_SLOW_FIGURE_TEST=1`.

The release gates are:

```shell
MPLCONFIGDIR=/tmp/kcon-mpl XDG_CACHE_HOME=/tmp/kcon-cache \
  .venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
git diff --check
.venv/bin/python -m pip check
```

## Remaining limitations

- Exact Fig. 3 coordinates and the paper's random seed are unpublished.
- The `N_l=5` workflow may not produce an incumbent within the default
  open-source-solver time limit.
- The versioned `N_l=2` result is not comparable to the paper's reported
  Scenario-I `epsilon=10.40 kJ` as an exact reproduction.
- Table III Scenarios II–VII, Table IV's eleven configurations and 20-topology
  averaging, Fig. 3(c)–(i), and Section IV-D survival analysis are outside v1.

# Error Resolution Report

Date: 22 July 2026

## Observed failures

The initial verification run produced 16 failed tests, 25 setup errors, and 53
passing tests. Most failures were cascading errors: environment construction
failed before the model or solver could run. Ruff also reported an undefined
name and multiple formatting violations.

After the first repair, model construction succeeded but every solvable fixture
was reported infeasible. This exposed two additional model-file corruptions.

## Root causes and fixes

### 1. Undefined `maximum_path`

File: `src/kcon_uwsn/environment.py`

`build_explicit_connectivity_partition` compared `kappa` with
`maximum_path`, but the function parameter is named `maximum_paths`. This
raised `NameError` for every environment that constructed a connectivity
partition.

Fix: restored the comparison to:

```python
if kappa > maximum_paths:
```

### 2. Invalid base-station attribute

File: `src/kcon_uwsn/model.py`

Constraint (7) referenced `env.network.bs_indexn`, which does not exist. The
correct `NetworkEnvironment` property is `bs_index`.

Fix: restored the base-station branch to:

```python
elif node == env.network.bs_index:
```

### 3. Incoming flow was omitted from Constraint (7)

File: `src/kcon_uwsn/model.py`

The intended flow balance is outgoing flow minus incoming flow. The subtraction
had been split into a separate standalone expression:

```python
balance = pulp.lpSum(outgoing_terms)
-pulp.lpSum(incoming_terms)
```

Python evaluates the second line and discards its result, so `balance`
contained only outgoing flow. This made otherwise valid models infeasible.

Fix: enclosed the full subtraction in one expression:

```python
balance = (
    pulp.lpSum(outgoing_terms)
    - pulp.lpSum(incoming_terms)
)
```

This restores the paper's Constraint (7) at source, relay, and base-station
nodes.

### 4. Formatting failures

Several core files contained nonstandard spacing and overlong lines. Ruff
formatting was applied repository-wide. This was mechanical formatting; the
three corrections above are the behavioral fixes.

## Verification

The following checks now pass:

- Full regular test suite: **94 passed, 1 optional slow test skipped**.
- Ruff lint: passed.
- Ruff formatting check: passed.
- Python dependency check: passed.

Real solver executions were also completed:

### HiGHS, four-sensor model

```shell
kcon-uwsn \
  --sensors 4 \
  --volume-km 0.2 0.2 0.1 \
  --connectivity-counts 4 0 0 \
  --two-dimensional \
  --time-limit 30 \
  --mip-gap 0
```

Result: optimal, `epsilon=1.460161 kJ`, zero energy and airtime residuals.

### HiGHS, 12-sensor approximate figure workflow

```shell
kcon-uwsn \
  --approximate-figure-3 \
  --seed 42 \
  --time-limit 45 \
  --output-dir results
```

Result: optimal within the requested solver tolerance,
`epsilon=23.771310 kJ`, achieved gap `11.3998%`, zero energy and airtime
residuals, and all four output artifacts generated.

### CBC fallback

A two-sensor model also solved optimally with CBC in approximately 0.2 seconds.
Its recomputed energy residual was `4.646e-06 J`, which is within normal CBC
floating-point feasibility tolerance.

## Operational note

`--figure-3` uses the paper-model `N_l=5` formulation and may legitimately
return no incumbent within its time limit. For a quick verified end-to-end run,
use `--approximate-figure-3`; its filenames and metadata explicitly disclose
the `N_l=2` approximation.

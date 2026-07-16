# k-con_UWSN

A paper-traceable implementation of:

> C. Tantur Karagul, M. B. Akgun, H. U. Yildiz, and B. Tavli,
> “Mitigating Energy Cost of Connection Reliability in UWSNs Through
> Non-uniform k-Connectivity,” IEEE Internet of Things Journal, 2025.

Development follows the reviewed stages in [`plan.md`](plan.md). Decisions,
assumptions, and verification results are recorded chronologically in
[`implementation_process.md`](implementation_process.md), while
[`docs/paper_traceability.md`](docs/paper_traceability.md) maps code and tests
to paper sections, equations, tables, and figures.

## Current scope

Stages 0–10 provide paper parameters, complete environment preprocessing, and
the PuLP formulation through Constraints (7)–(25), including routing,
disjointness, control traffic, energy, bandwidth, and interference. Stage 11
adds solver-independent solution/path/resource diagnostics. Stages 12–13 add
the CLI runner and Section IV-B Fig. 3(a)/(b) generation.

## Development setup

```shell
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

PuLP and the open-source HiGHS backend are installed with the project.

## Run a small model

```shell
kcon-uwsn \
  --sensors 4 \
  --volume-km 0.2 0.2 0.1 \
  --connectivity-counts 4 0 0 \
  --two-dimensional
```

Use `--solver cbc` to select the bundled open-source CBC fallback.

## Generate Fig. 3(a) and Fig. 3(b)

```shell
kcon-uwsn --figure-3 --seed 42 --output-dir results
```

This creates separate topology/Scenario-I PNGs, a combined image, and JSON
metadata. The paper does not publish its 12 sensor coordinates or random seed,
so the output is a deterministic methodological reproduction.

The standard model retains Table I `N_l=5`. The figure workflow explicitly
uses `N_l=2` for open-source solver tractability; this deviation is recorded in
the generated metadata and [`implementation_process.md`](implementation_process.md).

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

Stages 0–1 provide the Python package scaffolding and immutable paper
parameters. The environment, MILP, runner, and figure generation are added in
later reviewed stages.

## Development setup

```shell
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

PuLP and HiGHS will be added when MILP implementation begins.

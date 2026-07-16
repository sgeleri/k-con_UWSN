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

Stages 0–5 provide paper parameters, network/acoustic/interference preprocessing,
non-uniform connectivity partitions, and the PuLP variables/objective. Routing,
resource constraints, the runner, and figure generation follow in later
reviewed stages.

## Development setup

```shell
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

PuLP and the open-source HiGHS backend are installed with the project.

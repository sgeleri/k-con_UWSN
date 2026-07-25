# k-con_UWSN

A paper-traceable implementation of:

> C. Tantur Karagul, M. B. Akgun, H. U. Yildiz, and B. Tavli,
> “Mitigating Energy Cost of Connection Reliability in UWSNs Through
> Non-uniform k-Connectivity,” IEEE Internet of Things Journal, 2025.

Development follows the reviewed stages in `[plan.md](plan.md)`. Decisions,
assumptions, and verification results are recorded chronologically in
`[implementation_process.md](implementation_process.md)`, while
`[docs/paper_traceability.md](docs/paper_traceability.md)` maps code and tests
to paper sections, equations, tables, and figures.

## Current scope

Stages 0–10 provide paper parameters, complete environment preprocessing, and
the PuLP formulation through Constraints (7)–(25), including routing,
disjointness, control traffic, energy, bandwidth, and interference. Stage 11
adds solver-independent solution/path/resource diagnostics. Stages 12–13 add
the CLI runner and Section IV-B Fig. 3(a)/(b) generation. Stage 14 audits
equation fidelity, solver-result semantics, tests, and reproducibility.

## Development setup

```shell
python -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements-lock.txt -e ".[dev]"
pytest
ruff check .
ruff format --check .
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
Exit code 0 means optimal under the requested solver tolerance, 2 means no
valid incumbent, and 3 means a feasible incumbent whose optimality is unproven.

## Generate Scenario-I figures

Paper-model workflow (`N_l=5`, 1% requested gap):

```shell
kcon-uwsn --figure-3 --seed 42 --output-dir results
```

This may require substantially more time than the default limit. The paper does
not publish its 12 sensor coordinates or random seed, so even this workflow is
a methodological reproduction rather than an exact numerical reproduction.

Tractable approximation (`N_l=2`, 15% requested gap):

```shell
kcon-uwsn --approximate-figure-3 --seed 42 --output-dir results
```

Approximate files and metadata are explicitly named as such. The canonical
approximate artifacts under `results/` are versioned. JSON metadata records
software versions, solver configuration, termination reason, achieved MIP gap,
PNG hashes, and the `N_l=2` model deviation.
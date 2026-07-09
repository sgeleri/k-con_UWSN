# Implementation Process

This document is the chronological technical decision log for the
paper-traceable implementation of:

> C. Tantur Karagul, M. B. Akgun, H. U. Yildiz, and B. Tavli,
> “Mitigating Energy Cost of Connection Reliability in UWSNs Through
> Non-uniform k-Connectivity,” IEEE Internet of Things Journal, 2025.

The implementation is developed one reviewed stage at a time according to
[`plan.md`](plan.md). Existing entries are retained when decisions change;
superseded decisions are marked explicitly.

## Record format

Each completed stage records:

- Scope completed and files changed.
- Paper sections, equations, tables, and figures used.
- Design decisions and rationale.
- Assumptions, ambiguities, and implementation-specific behavior.
- Verification commands and results.
- Differences from the paper.
- Items requiring review before the next stage.

## Initial decisions

- Repository: standalone `k-con_UWSN`.
- Initial modeling stack: PuLP with the open-source HiGHS solver.
- Gurobi is deferred to preserve the one-year academic Named-User license for
  possible later work.
- Implementation order: parameters and environment, grouped MILP constraints,
  solution extraction, runner, then figures.
- Code uses BS index `0`; the paper uses BS index `1`.
- Direct paper implementations receive nearby section/equation/table/figure
  comments and matching test references.
- Primary visual deliverables are Section IV-B Fig. 3(a) Network Topology and
  Fig. 3(b) Scenario-I.
- The paper does not publish the 12 sensor coordinates or random seed used in
  Fig. 3. The figures will be deterministic methodological reproductions, not
  claims of exact numerical or pixel-level reconstruction.

## Stage log

Stage entries will be appended here as implementation proceeds.

# Paper Review Report

## Scope and source

This report reviews **“Mitigating Energy Cost of Connection Reliability in UWSNs Through Non-uniform k-Connectivity”** by Cagla Tantur Karagul, Mehmet Burak Akgun, Huseyin Ugur Yildiz, and Bulent Tavli.

The repository currently contains only a README naming the paper, not a local copy of the paper. This report is therefore based on the authors’ [publicly available PDF](https://huguryildiz.com/files/papers/journal/tantur2025mitigating.pdf), published in the *IEEE Internet of Things Journal*, volume 12, issue 22, pages 47817–47826 (2025), DOI [10.1109/JIOT.2025.3603829](https://doi.org/10.1109/JIOT.2025.3603829).

## Executive summary

The paper addresses a central tradeoff in underwater wireless sensor networks (UWSNs): additional independent paths to a base station improve resilience, but maintaining those paths consumes scarce battery energy. Instead of assigning the same connectivity requirement to every sensor, the authors propose **non-uniform k-connectivity**. Critical sensors receive more node-disjoint paths, while less critical sensors retain fewer paths.

The authors formulate routing, connectivity, traffic, interference, and energy use as a mixed-integer linear program (MILP). Its objective minimizes the energy consumed by the network’s most energy-intensive node. Assuming equal initial battery capacities, minimizing this bottleneck is equivalent to maximizing the time until the first node exhausts its battery.

The numerical results support the main claim: selective redundancy can preserve high reliability for important sensors at substantially lower energy cost than uniform high-k connectivity. In one 30-node, 3 km configuration, assigning only five sensors two paths and the remaining 25 one path produces a reported network lifetime 51.40% higher than assigning all sensors two paths. The paper does not, however, demonstrate a deployable distributed protocol; it establishes an optimization benchmark under static and idealized assumptions.

## Problem and proposed solution

For this study, a sensor is k-connected when it has at least `k` node-disjoint routes to the base station. Such redundancy allows traffic to survive failures along some routes. Uniform k-connectivity applies the same `k` to every sensor and can waste energy when only part of the network carries mission-critical data.

The proposed alternative partitions sensors into sets:

- `W1`: sensors requiring at least one path;
- `W2`: sensors requiring at least two node-disjoint paths;
- `W3`: sensors requiring at least three node-disjoint paths.

This makes reliability an application-level allocation decision. A network operator can reserve expensive redundancy for nodes whose loss would be most damaging.

## Model and method

### Network assumptions

The modeled network has:

- one static base station at a top corner of a rectangular deployment volume;
- static, anchored sensors placed uniformly at random;
- single-hop or multi-hop acoustic communication;
- ten transmission power levels with ranges from 100 m to 1,000 m;
- one 1,024-bit data packet generated per sensor per 300-second round;
- 256-bit control packets sent at relative frequency `ξ`;
- a 2,500 bit/s data rate and an interference-range multiplier of 1.7.

The main experiments use 30 sensors, 1 km width, 0.3 km depth, and deployment lengths of 1–3 km. Results for the larger configurations are averages over 20 random topologies.

### Energy model

Transmission cost depends on distance, acoustic spreading, and absorption at 25 kHz. Reception has a fixed per-bit cost. The model includes energy spent transmitting and receiving both data and control traffic, including relayed traffic.

The objective variable, `ε`, is the largest energy expenditure among all sensors. The MILP minimizes `ε`. Network lifetime is treated as inversely proportional to `ε`, provided all sensors begin with equal battery energy.

### Optimization constraints

The MILP includes constraints for:

- flow conservation from each source to the base station;
- packet generation and routing;
- non-bifurcating paths;
- node- and link-disjoint routes;
- per-node connectivity requirements;
- control traffic on active paths;
- transmission and reception energy;
- bandwidth consumption and local interference.

The model is implemented in Python and solved with Gurobi. Because MILP solutions are exact for the stated model and parameters, the results act as an optimal benchmark for the modeled scenarios.

## Key findings

### Connectivity and control traffic both consume substantial energy

At a deployment length of 3 km, increasing control-packet frequency from `ξ = 0.25` to `ξ = 4` raises `ε` for a uniformly 3-connected network from 55.31 kJ to 308.70 kJ. At `ξ = 1`, `ε` is:

| Uniform connectivity | Maximum node energy, `ε` |
|---|---:|
| k = 1 | 62.83 kJ |
| k = 2 | 76.61 kJ |
| k = 3 | 121.96 kJ |

This shows that control-plane overhead is not negligible and that its cost grows with the number of maintained paths.

### Non-uniform assignments improve the lifetime/reliability tradeoff

For 30-node deployments of length 3 km:

| Assignment | Maximum node energy, `ε` |
|---|---:|
| 25 nodes at k=1, 5 at k=2 | 63.56 kJ |
| 20 at k=1, 5 at k=2, 5 at k=3 | 69.37 kJ |
| all 30 at k=2 | 96.23 kJ |
| all 30 at k=3 | 108.45 kJ |

The paper reports:

- 51.40% greater lifetime for the first assignment than uniform k=2;
- 36.04% lower lifetime for uniform k=3 than the mixed 20/5/5 assignment;
- 15.97% greater lifetime in a 12-node example when half the nodes use k=3 and half k=1, compared with uniform k=3.

These comparisons show that deployment size and path length amplify the benefit of selective redundancy.

### Higher k improves survival under random failures

For a mixed 30-node configuration, after ten random node failures:

| Initial connectivity | Probability of remaining connected |
|---|---:|
| k = 1 | 0.52 |
| k = 2 | 0.84 |
| k = 3 | 0.92 |

The resilience gain is therefore meaningful, but so is its energy cost. Non-uniform assignment provides a mechanism to decide where that cost is justified.

## Strengths

- **Clear practical tradeoff:** The study connects path redundancy directly to the battery bottleneck that limits UWSNs.
- **More realistic overhead accounting:** It includes control packets, relaying, reception, and interference rather than counting only source data transmission.
- **Flexible formulation:** Per-group connectivity requirements permit arbitrary non-uniform assignments.
- **Optimal reference point:** Exact MILP solutions provide useful lower bounds on bottleneck energy for future heuristics.
- **Broad parameter sweep:** The evaluation varies connectivity mixes, deployment length, and control frequency and includes multiple random topologies.

## Limitations and open questions

- **Optimization is not an operational protocol.** A centralized Gurobi solution assumes global topology and traffic knowledge. The paper does not specify how routes are discovered, maintained, or recomputed in a deployed network.
- **Scalability is not reported.** MILPs with per-source, per-path, and per-link variables can grow quickly, but solver runtimes, optimality gaps, and hardware are not presented.
- **Static topology assumptions are restrictive.** Currents, mobile sensors, moving base stations, time-varying acoustic channels, packet loss, and link asymmetry are outside the evaluated model.
- **Lifetime has a narrow definition.** The objective balances the most heavily loaded node and assumes equal initial batteries. Other definitions—coverage loss, partition time, or mission utility—could produce different routing choices.
- **Critical nodes are predetermined or randomly assigned.** The study does not derive criticality from sensing coverage, event importance, traffic demand, or risk.
- **Failure analysis preserves original routes.** It measures whether precomputed paths survive random node removals, without rerouting, correlated failures, or link failures.
- **Statistical evidence is limited.** Averages over 20 topologies are useful, but confidence intervals and significance tests are not supplied.
- **The comparison baseline is narrow.** Non-uniform optimum is compared mainly with uniform optimum; practical multipath protocols and approximation algorithms are not evaluated.

These limitations do not invalidate the optimization results, but they constrain the claim to the modeled settings.

## Implications for this repository

A faithful implementation should separate four concerns:

1. **Topology generation:** create reproducible 3D sensor deployments and base-station placement from a recorded random seed.
2. **Physical and energy model:** implement the ten transmission ranges, Thorp absorption formula, per-bit transmission/reception energy, packet sizes, and control frequency.
3. **MILP construction:** model source/path/link flows, path activation, node-disjointness, group-specific `k`, interference, and minimax energy.
4. **Experiment runner and validation:** reproduce the paper’s tables and expose solver status, runtime, objective value, seed, and parameter configuration.

The first validation targets should be the energy values in Tables II and IV. Tests should also verify flow conservation, required path counts, node-disjointness, and monotonic behavior when control frequency or uniform `k` increases. Any difference from the paper should be reported rather than hidden, especially because some details—such as random seeds and solver settings—are not specified.

For use beyond reproduction, a scalable heuristic or distributed routing method should be compared against the MILP optimum on small networks, then evaluated under dynamic channels and failures.

## Conclusion

The paper makes a convincing case that uniform redundancy is often an inefficient reliability policy for battery-limited UWSNs. Its main contribution is a MILP framework showing how differentiated connectivity can protect critical sensors while extending network lifetime. The reported gains are substantial, especially in longer deployments, but represent an idealized centralized optimum. The next engineering step is to reproduce the benchmark faithfully and then develop practical algorithms whose energy and resilience can be measured against it.

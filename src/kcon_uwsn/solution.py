"""Solver-independent extraction and diagnostics for solved paper MILPs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import pulp

from .environment import DirectedArc, EnvironmentData
from .model import FlowKey, ModelVars, PathKey


def _frozen_mapping(values: Mapping[object, object]) -> Mapping[object, object]:
    return MappingProxyType(dict(values))


@dataclass(frozen=True, slots=True)
class Solution:
    """Structured values and paper-specific diagnostics from one solve."""

    status_code: int
    status: str
    termination_reason: str
    pulp_status: str
    pulp_solution_status: str
    objective_energy_j: float | None
    best_bound_j: float | None
    relative_gap: float | None
    solve_time_s: float | None

    data_flow_packets: Mapping[FlowKey, float]
    control_flow_packets: Mapping[FlowKey, float]
    active_arcs: Mapping[FlowKey, int]
    path_packets: Mapping[PathKey, float]
    paths: Mapping[PathKey, tuple[DirectedArc, ...]]
    extraneous_arcs: Mapping[PathKey, tuple[DirectedArc, ...]]

    node_energy_j: Mapping[int, float]
    node_airtime_s: Mapping[int, float]
    active_path_count_by_source: Mapping[int, int]
    packet_balance_error_by_source: Mapping[int, float]
    connectivity_shortfall_by_source: Mapping[int, int]
    maximum_energy_violation_j: float
    maximum_airtime_violation_s: float

    def __post_init__(self) -> None:
        mapping_fields = (
            "data_flow_packets",
            "control_flow_packets",
            "active_arcs",
            "path_packets",
            "paths",
            "extraneous_arcs",
            "node_energy_j",
            "node_airtime_s",
            "active_path_count_by_source",
            "packet_balance_error_by_source",
            "connectivity_shortfall_by_source",
        )

        for field_name in mapping_fields :
            object.__setattr__(
                self,
                field_name,
                _frozen_mapping(getattr(self, field_name)),
            )

    @property
    def has_incumbent(self) -> bool :
        """Return whether the solver supplied variable values."""

        return self.objective_energy_j is not None


def _value(variable: pulp.LpVariable) -> float :
    value = pulp.value(variable)

    if value is None :
        raise ValueError(f"variable {variable.name} has no solution value")
    return float(value)


def _sparse_values(
    variables : Mapping[object, pulp.LpVariable],
    tolerance : float,
) -> dict[object, float] :
    return {
        key : value
        for key, variable in variables.items()
        if abs(value := _value(variable)) > tolerance
    }


def _ordered_path(
    source      : int,
    bs_index    : int,
    active_arcs : tuple[DirectedArc, ...],
) -> tuple[tuple[DirectedArc, ...], tuple[DirectedArc, ...]] :
    """Extract the source-to-BS component and retain any extraneous arcs."""

    remaining                   = set(active_arcs)
    ordered : list[DirectedArc] = []
    current                     = source
    visited                     = {source}

    while current != bs_index :
        outgoing = [arc for arc in remaining if arc[0] == current]
        if len(outgoing) != 1 :
            raise ValueError(
                f"active path from source {source} has {len(outgoing)} "
                f"next hops at node {current}"
            )
        arc = outgoing[0]
        ordered.append(arc)
        remaining.remove(arc)
        current = arc[1]

        if current in visited :
            raise ValueError(f"active path from source {source} contains a cycle")
        visited.add(current)

    return tuple(ordered), tuple(sorted(remaining))


def _reconstruct_paths(
    env             : EnvironmentData,
    active_arcs     : Mapping[FlowKey, int],
    path_packets    : Mapping[PathKey, float],
) -> tuple[
    dict[PathKey, tuple[DirectedArc, ...]],
    dict[PathKey, tuple[DirectedArc, ...]],
] :
    paths       : dict[PathKey, tuple[DirectedArc, ...]] = {}
    extraneous  : dict[PathKey, tuple[DirectedArc, ...]] = {}

    for path_key in path_packets :
        source, path = path_key
        selected     = tuple(
            (transmitter, receiver)
            for (
                key_source,
                key_path,
                transmitter,
                receiver,
            ) in active_arcs
            if key_source == source and key_path == path
        )
        paths[path_key], unused = _ordered_path(
            source,
            env.network.bs_index,
            selected,
        )
        if unused:
            extraneous[path_key] = unused
    return paths, extraneous


def _node_energy(
    env             : EnvironmentData,
    data_flow       : Mapping[FlowKey, float],
    control_flow    : Mapping[FlowKey, float],
) -> dict[int, float] :
    """Evaluate Constraint (21) from extracted values."""

    data_bits                   = env.paper.network.data_packet_size_bits
    control_bits                = env.paper.network.control_packet_size_bits
    energies : dict[int, float] = {}

    for node in env.network.sensors :
        total = 0.0
        for source in env.network.sensors :
            for path in range(1, env.paper.network.maximum_paths + 1) :
                for arc in env.network.arcs :
                    key  = (source, path, *arc)
                    bits = (
                        data_flow.get(key, 0.0) * data_bits
                        + control_flow.get(key, 0.0) * control_bits
                    )

                    if arc[0] == node:
                        total += (
                            env.energy.link_transmission_energy_j_per_bit[arc] * bits
                        )

                    if arc[1] == node:
                        total += env.energy.reception_energy_j_per_bit * bits
        energies[node] = total
    return energies


def _node_airtime(
    env             : EnvironmentData,
    data_flow       : Mapping[FlowKey, float],
    control_flow    : Mapping[FlowKey, float],
) -> dict[int, float] :
    """Evaluate Constraint (22) with the documented ``A\\{i}`` interpretation."""

    data_bits                  = env.paper.network.data_packet_size_bits
    control_bits               = env.paper.network.control_packet_size_bits
    data_rate                  = env.paper.network.data_rate_bps
    airtime : dict[int, float] = {}

    for node in env.network.nodes :
        interfering = {
            arc
            for arc in env.interference.interfering_arcs_by_node[node]
            if node not in arc
        }
        total = 0.0
        for source in env.network.sensors :
            for path in range(1, env.paper.network.maximum_paths + 1) :
                for arc in env.network.arcs:
                    key = (source, path, *arc)
                    bits = (
                        data_flow.get(key, 0.0) * data_bits
                        + control_flow.get(key, 0.0) * control_bits
                    )

                    if arc[0] == node :
                        total += bits / data_rate

                    if arc[1] == node :
                        total += bits / data_rate
                    
                    if arc in interfering :
                        total += bits / data_rate
        airtime[node] = total
    return airtime


def _status_only_solution(
    problem : pulp.LpProblem,
    *,
    status  : str = "No Solution",
) -> Solution :
    termination_reason, best_bound, relative_gap = _solver_diagnostics(problem)
    return Solution(
        status_code                      = problem.status,
        status                           = status,
        termination_reason               = termination_reason,
        pulp_status                      = pulp.LpStatus[problem.status],
        pulp_solution_status             = pulp.LpSolution[problem.sol_status],
        objective_energy_j               = None,
        best_bound_j                     = best_bound,
        relative_gap                     = relative_gap,
        solve_time_s                     = getattr(problem, "solutionTime", None),
        data_flow_packets                = {},
        control_flow_packets             = {},
        active_arcs                      = {},
        path_packets                     = {},
        paths                            = {},
        extraneous_arcs                  = {},
        node_energy_j                    = {},
        node_airtime_s                   = {},
        active_path_count_by_source      = {},
        packet_balance_error_by_source   = {},
        connectivity_shortfall_by_source = {},
        maximum_energy_violation_j       = 0.0,
        maximum_airtime_violation_s      = 0.0,
    )


def _has_valid_integer_incumbent(
    problem     : pulp.LpProblem,
    variables   : ModelVars,
    tolerance   : float,
) -> bool :
    """Reject solver relaxation values mislabeled as a MIP incumbent."""

    integer_variables = (
        *variables.data_flow.values(),
        *variables.control_flow.values(),
        *variables.arc_used.values(),
        *variables.path_packets.values(),
    )
    if any(
        variable.varValue is None
        or abs(float(variable.varValue) - round(float(variable.varValue))) > tolerance
        for variable in integer_variables
    ) :
        return False
    feasibility_tolerance = max(tolerance, 1e-5)
    return all(
        constraint.valid(feasibility_tolerance) for constraint in problem.constraints()
    )


def _solver_diagnostics(
    problem: pulp.LpProblem,
) -> tuple[str, float | None, float | None] :
    """Read termination reason and MIP bounds when the backend exposes them."""

    solver_model = getattr(problem, "solverModel", None)
    if solver_model is None :
        return pulp.LpStatus[problem.status], None, None
    try:
        reason = solver_model.modelStatusToString(solver_model.getModelStatus())
        info   = solver_model.getInfo()
        return reason, float(info.mip_dual_bound), float(info.mip_gap)
    except (AttributeError, TypeError, ValueError):
        return pulp.LpStatus[problem.status], None, None


def extract_solution(
    problem     : pulp.LpProblem,
    variables   : ModelVars,
    env         : EnvironmentData,
    *,
    tolerance   : float = 1e-7,
) -> Solution :
    """Extract values, paths, and diagnostics without exposing PuLP objects.

    Paper references:
    - Objective (6): ``objective_energy_j``.
    - Constraints (8), (18), (21), and (22): diagnostic residuals.
    - Constraints (12)–(20): ordered source-to-BS path reconstruction.
    """

    if tolerance <= 0 :
        raise ValueError("tolerance must be positive")
    
    incumbent_statuses = {
        pulp.LpSolutionOptimal,
        pulp.LpSolutionIntegerFeasible,
    }

    if problem.sol_status not in incumbent_statuses :
        return _status_only_solution(problem)
    if not _has_valid_integer_incumbent(problem, variables, tolerance):
        return _status_only_solution(problem, status="Invalid Incumbent")

    objective    = _value(variables.maximum_sensor_energy)
    data_flow    = _sparse_values(variables.data_flow, tolerance)
    control_flow = _sparse_values(variables.control_flow, tolerance)
    path_packets = _sparse_values(variables.path_packets, tolerance)
    active_arcs  = {
        key : 1 for key, variable in variables.arc_used.items() if _value(variable) > 0.5
    }
    paths, extraneous_arcs = _reconstruct_paths(env, active_arcs, path_packets)
    node_energy            = _node_energy(env, data_flow, control_flow)
    node_airtime           = _node_airtime(env, data_flow, control_flow)

    path_counts = {
        source : sum(1 for path_source, _ in paths if path_source == source)
        for source in env.network.sensors
    }
    expected_packets = (
        env.paper.network.packets_per_sensor_per_round
        * env.paper.network.number_of_rounds
    )
    packet_errors = {
        source : abs(
            sum(
                value
                for (path_source, _), value in path_packets.items()
                if path_source == source
            )
            - expected_packets
        )
        for source in env.network.sensors
    }
    shortfalls = {
        source : max(
            0,
            env.connectivity.kappa_by_sensor[source] - path_counts[source],
        )
        for source in env.network.sensors
    }
    available_time = (
        env.paper.network.number_of_rounds * env.paper.network.round_duration_s
    )
    termination_reason, best_bound, relative_gap = _solver_diagnostics(problem)
    if problem.sol_status == pulp.LpSolutionOptimal:
        solution_status = (
            "Optimal within solver tolerance"
            if relative_gap is not None and relative_gap > tolerance
            else "Optimal"
        )
    else:
        solution_status = "Feasible"

    return Solution(
        status_code                         = problem.status,
        status                              = solution_status,
        termination_reason                  = termination_reason,
        pulp_status                         = pulp.LpStatus[problem.status],
        pulp_solution_status                = pulp.LpSolution[problem.sol_status],
        objective_energy_j                  = objective,
        best_bound_j                        = best_bound,
        relative_gap                        = relative_gap,
        solve_time_s                        = getattr(problem, "solutionTime", None),
        data_flow_packets                   = data_flow,
        control_flow_packets                = control_flow,
        active_arcs                         = active_arcs,
        path_packets                        = path_packets,
        paths                               = paths,
        extraneous_arcs                     = extraneous_arcs,
        node_energy_j                       = node_energy,
        node_airtime_s                      = node_airtime,
        active_path_count_by_source         = path_counts,
        packet_balance_error_by_source      = packet_errors,
        connectivity_shortfall_by_source    = shortfalls,
        maximum_energy_violation_j          = max(
            0.0,
            max(node_energy.values(), default=0.0) - objective,
        ),
        maximum_airtime_violation_s         = max(
            0.0,
            max(node_airtime.values(), default=0.0) - available_time,
        ),
    )

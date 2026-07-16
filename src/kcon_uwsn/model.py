"""PuLP formulation of the Tantur et al. (2025) MILP.

Stage 5 introduces only the Section III-C variables, their domains, and
Objective (6). Constraints are added in subsequent reviewed stages.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import pulp

from .environment import EnvironmentData

FlowKey = tuple[int, int, int, int]
PathKey = tuple[int, int]


@dataclass(frozen=True, slots=True)
class ModelVars :
    """Typed handles for all decision variables defined in Section III-C."""

    # Keys are (source k, path l, transmitter i, receiver j).
    data_flow       : Mapping[FlowKey, pulp.LpVariable]
    control_flow    : Mapping[FlowKey, pulp.LpVariable]
    arc_used        : Mapping[FlowKey, pulp.LpVariable]

    # Keys are (source k, path l).
    path_packets            : Mapping[PathKey, pulp.LpVariable]
    maximum_sensor_energy   : pulp.LpVariable

    def __post_init__(self) -> None :
        object.__setattr__(
            self,
            "data_flow",
            MappingProxyType(dict(self.data_flow)),
        )
        object.__setattr__(
            self,
            "control_flow",
            MappingProxyType(dict(self.control_flow)),
        )
        object.__setattr__(
            self,
            "arc_used",
            MappingProxyType(dict(self.arc_used)),
        )
        object.__setattr__(
            self,
            "path_packets",
            MappingProxyType(dict(self.path_packets)),
        )


def _flow_variable_name(
    symbol      : str,
    source      : int,
    path        : int,
    transmitter : int,
    receiver    : int,
) -> str :
    return f"{symbol}_k{source}_l{path}_i{transmitter}_j{receiver}"


def build_model(env: EnvironmentData) -> tuple[pulp.LpProblem, ModelVars] :
    """Create variables, domains, and Objective (6).

    Paper: Section III-C, Objective (6), and Constraints (23)–(25).

    Path indices remain one-based to match ``l in {1,...,N_l}`` in the paper.
    Node indices remain zero-based according to the environment convention.
    """

    problem = pulp.LpProblem(
        name  = "tantur_2025_non_uniform_k_connectivity",
        sense = pulp.LpMinimize,
    )
    sensors = env.network.sensors
    arcs    = env.network.arcs
    paths   = tuple(range(1, env.paper.network.maximum_paths + 1))

    flow_keys = tuple(
        (source, path, transmitter, receiver)
        for source in sensors
        for path in paths
        for transmitter, receiver in arcs
    )
    path_keys = tuple(
        (source, path)
        for source in sensors
        for path in paths
    )

    # Paper: Section III-C and Constraint (23), f^kl_ij >= 0 integer.
    data_flow = {
        key : problem.add_variable(
            _flow_variable_name("f", *key),
            lowBound=0,
            cat=pulp.LpInteger,
        )
        for key in flow_keys
    }

    # Paper: Section III-C and Constraint (23), g^kl_ij >= 0 integer.
    control_flow = {
        key : problem.add_variable(
            _flow_variable_name("g", *key),
            lowBound=0,
            cat=pulp.LpInteger,
        )
        for key in flow_keys
    }

    # Paper: Section III-C and Constraint (24), h^kl_ij is binary.
    arc_used = {
        key : problem.add_variable(
            _flow_variable_name("h", *key),
            cat=pulp.LpBinary,
        )
        for key in flow_keys
    }

    # Paper: Section III-C and Constraint (25), p^l_k >= 0 integer.
    path_packets = {
        key : problem.add_variable(
            f"p_k{key[0]}_l{key[1]}",
            lowBound=0,
            cat=pulp.LpInteger,
        )
        for key in path_keys
    }

    # Paper: Section III-C, epsilon is the most energy-consuming sensor's
    # total energy. A non-negative continuous variable is sufficient.
    maximum_sensor_energy = problem.add_variable(
        "epsilon",
        lowBound=0,
        cat=pulp.LpContinuous,
    )

    variables = ModelVars(
        data_flow=data_flow,
        control_flow=control_flow,
        arc_used=arc_used,
        path_packets=path_packets,
        maximum_sensor_energy=maximum_sensor_energy,
    )

    # Paper: Section III-C, Objective (6), minimize epsilon.
    problem += maximum_sensor_energy, "objective_06_minimize_epsilon"

    return problem, variables

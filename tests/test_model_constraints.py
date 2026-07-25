"""Tests for paper Constraints (7)–(22), implemented in Stages 6–10."""

import numpy as np
import pulp
import pytest

from kcon_uwsn.environment import (
    Deployment,
    EnvironmentData,
    build_acoustic_energy_environment,
    build_explicit_connectivity_partition,
    build_interference_environment,
    build_network_environment,
)
from kcon_uwsn.model import ModelVars, build_model
from kcon_uwsn.params import ExperimentParameters, PaperParameters


def _fixed_environment(
    connectivity_counts: tuple[int, int, int] = (2, 0, 0),
) -> EnvironmentData:
    paper = PaperParameters()
    experiment = ExperimentParameters(
        number_of_sensors=2,
        volume_km=(0.3, 0.1, 0.1),
        connectivity_counts=connectivity_counts,
        random_seed=1,
    )
    deployment = Deployment(
        np.array(
            [
                [0.0, 0.0, 0.0],
                [100.0, 0.0, 0.0],
                [300.0, 0.0, 0.0],
            ]
        )
    )
    network = build_network_environment(
        deployment,
        paper.power_levels.ranges_m[-1],
    )
    energy = build_acoustic_energy_environment(
        network,
        acoustic=paper.acoustic,
        power_levels=paper.power_levels,
    )
    sets_by_kappa: dict[int, tuple[int, ...]]
    if connectivity_counts == (2, 0, 0):
        sets_by_kappa = {1: (1, 2), 2: (), 3: ()}
    elif connectivity_counts == (0, 2, 0):
        sets_by_kappa = {1: (), 2: (1, 2), 3: ()}
    else:
        raise ValueError("unsupported test connectivity_counts")
    connectivity = build_explicit_connectivity_partition(
        network.sensors,
        sets_by_kappa,
    )
    interference = build_interference_environment(
        network,
        paper.network.interference_range_multiplier,
    )
    return EnvironmentData(
        experiment=experiment,
        paper=paper,
        energy=energy,
        connectivity=connectivity,
        interference=interference,
    )


@pytest.fixture
def complete_model() -> tuple[EnvironmentData, pulp.LpProblem, ModelVars]:
    environment = _fixed_environment()
    problem, variables = build_model(environment)
    return environment, problem, variables


def test_all_equation_groups_are_named_and_present(
    complete_model: tuple[EnvironmentData, pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Constraints (7)–(22)."""

    _, problem, _ = complete_model
    representative_names = (
        "c07_flow_i0_k1_l1",
        "c08_generated_k1",
        "c09_no_reentry_k1",
        "c10_flow_upper_k1_l1_i0_j1",
        "c11_flow_lower_k1_l1_i0_j1",
        "c12_single_next_i1_k1_l1",
        "c13_link_disjoint_k1_i0_j1",
        "c14_path_order_k1_l1",
        "c15_phantom_upper_k1_l1_i0_j1",
        "c16_phantom_lower_k1_l1_i0_j1",
        "c17_control_k1_l1_i0_j1",
        "c18_kappa_k1",
        "c19_node_out_i2_k1",
        "c20_node_in_i2_k1",
        "c21_energy_i1",
        "c22_bandwidth_i1",
    )

    assert all(
        problem.get_constraint_by_name(name) is not None
        for name in representative_names
    )


def test_flow_conservation_and_generation_constraints_solve(
    complete_model: tuple[EnvironmentData, pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Constraints (7)–(12)."""

    environment, problem, variables = complete_model
    status = problem.solve(pulp.HiGHS(msg=False))

    assert pulp.LpStatus[status] == "Optimal"
    generated = (
        environment.paper.network.packets_per_sensor_per_round
        * environment.paper.network.number_of_rounds
    )
    for source in environment.network.sensors:
        assert sum(
            pulp.value(variables.path_packets[(source, path)]) for path in range(1, 6)
        ) == pytest.approx(generated)
        for path in range(1, 6):
            for node in environment.network.nodes:
                constraint = problem.get_constraint_by_name(
                    f"c07_flow_i{node}_k{source}_l{path}"
                )
                assert abs(constraint.value()) <= 1e-7


def test_kappa_two_produces_two_node_disjoint_paths() -> None:
    """Paper: Constraints (13)–(16) and (18)–(20)."""

    environment = _fixed_environment((0, 2, 0))
    problem, variables = build_model(environment)
    status = problem.solve(pulp.HiGHS(msg=False))

    assert pulp.LpStatus[status] == "Optimal"
    for source in environment.network.sensors:
        used_starts = [
            (path, arc)
            for path in range(1, 6)
            for arc in environment.network.arcs
            if arc[0] == source
            and pulp.value(variables.arc_used[(source, path, *arc)]) > 0.5
        ]
        assert len(used_starts) >= 2
        assert len({path for path, _ in used_starts}) >= 2

        relay_usage: dict[int, set[int]] = {}
        for path in range(1, 6):
            for transmitter, receiver in environment.network.arcs:
                if (
                    pulp.value(
                        variables.arc_used[(source, path, transmitter, receiver)]
                    )
                    <= 0.5
                ):
                    continue
                for node in (transmitter, receiver):
                    if node not in (source, environment.network.bs_index):
                        relay_usage.setdefault(node, set()).add(path)
        assert all(len(paths) <= 1 for paths in relay_usage.values())


def test_control_flow_matches_constraint_17(
    complete_model: tuple[EnvironmentData, pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Constraint (17)."""

    environment, problem, variables = complete_model
    problem.solve(pulp.HiGHS(msg=False))
    expected_multiplier = (
        environment.experiment.control_to_data_frequency
        * environment.paper.network.number_of_rounds
    )

    for key, control in variables.control_flow.items():
        source, path, transmitter, receiver = key
        reverse = variables.arc_used[(source, path, receiver, transmitter)]
        expected = expected_multiplier * (
            pulp.value(variables.arc_used[key]) + pulp.value(reverse)
        )
        assert pulp.value(control) == pytest.approx(expected)


def test_constraint_21_energy_coefficients_match_tx_and_rx_terms(
    complete_model: tuple[EnvironmentData, pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Constraint (21)."""

    environment, problem, variables = complete_model
    constraint = problem.get_constraint_by_name("c21_energy_i1")
    tx_arc = (1, 0)
    rx_arc = (0, 1)
    tx_data = variables.data_flow[(1, 1, *tx_arc)]
    tx_control = variables.control_flow[(1, 1, *tx_arc)]
    rx_data = variables.data_flow[(1, 1, *rx_arc)]

    assert constraint.get(tx_data, 0.0) == pytest.approx(
        environment.energy.link_transmission_energy_j_per_bit[tx_arc]
        * environment.paper.network.data_packet_size_bits
    )
    assert constraint.get(tx_control, 0.0) == pytest.approx(
        environment.energy.link_transmission_energy_j_per_bit[tx_arc]
        * environment.paper.network.control_packet_size_bits
    )
    assert constraint.get(rx_data, 0.0) == pytest.approx(
        environment.energy.reception_energy_j_per_bit
        * environment.paper.network.data_packet_size_bits
    )
    assert constraint.get(variables.maximum_sensor_energy, 0.0) == -1


def test_constraint_22_has_tx_rx_and_nonincident_interference_terms(
    complete_model: tuple[EnvironmentData, pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Constraint (22) and Eq. (26)."""

    environment, problem, variables = complete_model
    constraint = problem.get_constraint_by_name("c22_bandwidth_i1")
    coefficient = (
        environment.paper.network.data_packet_size_bits
        / environment.paper.network.data_rate_bps
    )

    own_tx = variables.data_flow[(1, 1, 1, 0)]
    own_rx = variables.data_flow[(1, 1, 0, 1)]
    interfering = variables.data_flow[(1, 1, 0, 2)]

    assert constraint.get(own_tx, 0.0) == pytest.approx(coefficient)
    assert constraint.get(own_rx, 0.0) == pytest.approx(coefficient)
    assert environment.interference.indicator(1, (0, 2)) == 1
    assert constraint.get(interfering, 0.0) == pytest.approx(coefficient)

    # Arc 1->2 is incident to node 1 and is counted only as own transmission,
    # even though literal Eq. (26) also marks it as interfering at node 1.
    incident = variables.data_flow[(1, 1, 1, 2)]
    assert environment.interference.indicator(1, (1, 2)) == 1
    assert constraint.get(incident, 0.0) == pytest.approx(coefficient)


def test_complete_model_has_expected_constraint_count(
    complete_model: tuple[EnvironmentData, pulp.LpProblem, ModelVars],
) -> None:
    """Regression count for the two-sensor complete directed graph."""

    _, problem, _ = complete_model

    assert problem.numConstraints() == 385

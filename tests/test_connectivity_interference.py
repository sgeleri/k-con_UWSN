"""Tests for Stage 4 connectivity and interference preprocessing."""

import numpy as np
import pytest

from kcon_uwsn.environment import (
    Deployment,
    build_environment,
    build_explicit_connectivity_partition,
    build_interference_environment,
    build_network_environment,
    build_seeded_connectivity_partition,
)
from kcon_uwsn.params import ExperimentParameters


def test_explicit_partition_maps_disjoint_w_sets_to_kappa() -> None:
    """Paper: Section III-A, Constraint (18), and Table III."""

    partition = build_explicit_connectivity_partition(
        sensors=(1, 2, 3, 4),
        sets_by_kappa={1: (1, 2), 2: (3,), 3: (4,)},
    )

    assert partition.sets_by_kappa[1] == (1, 2)
    assert partition.kappa_by_sensor == {1: 1, 2: 1, 3: 2, 4: 3}


@pytest.mark.parametrize(
    "sets_by_kappa",
    [
        {1: (1, 2), 2: (2, 3)},
        {1: (1,), 2: (2,)},
        {1: (1, 2), 4: (3,)},
    ],
)
def test_explicit_partition_rejects_overlap_missing_nodes_and_invalid_kappa(
    sets_by_kappa: dict[int, tuple[int, ...]],
) -> None:
    """Paper: W is the disjoint union of valid W_n subsets."""

    with pytest.raises(ValueError):
        build_explicit_connectivity_partition(
            sensors=(1, 2, 3),
            sets_by_kappa=sets_by_kappa,
        )


def test_seeded_partition_is_reproducible_and_respects_counts() -> None:
    """Paper: Section IV-C uses random W_n assignment."""

    sensors = tuple(range(1, 11))
    first = build_seeded_connectivity_partition(
        sensors,
        (5, 3, 2),
        random_seed=42,
    )
    second = build_seeded_connectivity_partition(
        sensors,
        (5, 3, 2),
        random_seed=42,
    )

    assert first.sets_by_kappa == second.sets_by_kappa
    assert tuple(len(first.sets_by_kappa[kappa]) for kappa in (1, 2, 3)) == (
        5,
        3,
        2,
    )
    assert set(first.kappa_by_sensor) == set(sensors)


def test_environment_uses_independent_assignment_random_stream() -> None:
    experiment = ExperimentParameters(
        number_of_sensors=10,
        connectivity_counts=(5, 3, 2),
        random_seed=42,
    )
    environment = build_environment(experiment)
    assignment_seed = int(np.random.SeedSequence(42).spawn(2)[1].generate_state(1)[0])
    expected = build_seeded_connectivity_partition(
        environment.network.sensors,
        experiment.connectivity_counts,
        random_seed=assignment_seed,
    )

    assert environment.connectivity.sets_by_kappa == expected.sets_by_kappa


def test_partition_mappings_are_immutable() -> None:
    """Implementation decision: connectivity cannot mutate during a solve."""

    partition = build_explicit_connectivity_partition(
        sensors=(1, 2),
        sets_by_kappa={1: (1,), 2: (2,)},
    )

    with pytest.raises(TypeError):
        partition.kappa_by_sensor[1] = 2


def test_equation_26_true_and_false_branches() -> None:
    """Paper: Section III-C, Eq. (26), gamma*d_jm >= d_ji."""

    deployment = Deployment(
        np.array(
            [
                [0.0, 0.0, 0.0],
                [100.0, 0.0, 0.0],
                [300.0, 0.0, 0.0],
                [500.0, 0.0, 0.0],
            ]
        )
    )
    network = build_network_environment(deployment, 250.0)
    interference = build_interference_environment(network, 1.7)

    # Link 0->1 has length 100 m and interference reach 170 m from node 0.
    assert interference.indicator(1, (0, 1)) == 1
    assert interference.indicator(2, (0, 1)) == 0

    # Eq. (26) also evaluates true at the transmitter because d_jj=0.
    assert interference.indicator(0, (0, 1)) == 1


def test_interference_mapping_contains_all_nodes_and_is_sparse() -> None:
    """Paper: Eq. (26) is defined for every i in V and communication arc."""

    deployment = Deployment(
        np.array(
            [
                [0.0, 0.0, 0.0],
                [100.0, 0.0, 0.0],
                [300.0, 0.0, 0.0],
            ]
        )
    )
    network = build_network_environment(deployment, 250.0)
    interference = build_interference_environment(network, 1.7)

    assert set(interference.interfering_arcs_by_node) == set(network.nodes)
    assert (0, 1) not in interference.interfering_arcs_by_node[2]


def test_complete_environment_supports_explicit_table_iii_assignment() -> None:
    """Paper: Table III Scenario II-style explicit W_1/W_2 sets."""

    experiment = ExperimentParameters(
        number_of_sensors=4,
        volume_km=(0.2, 0.2, 0.1),
        connectivity_counts=(2, 2, 0),
        random_seed=5,
    )
    environment = build_environment(
        experiment,
        explicit_connectivity_sets={1: (3, 4), 2: (1, 2), 3: ()},
        two_dimensional=True,
    )

    assert environment.network.sensors == (1, 2, 3, 4)
    assert environment.connectivity.kappa_by_sensor == {1: 2, 2: 2, 3: 1, 4: 1}
    assert set(environment.energy.link_transmission_energy_j_per_bit) == set(
        environment.network.arcs
    )
    assert set(environment.interference.interfering_arcs_by_node) == set(
        environment.network.nodes
    )


def test_explicit_partition_counts_must_match_experiment() -> None:
    """Implementation consistency check for Table III/IV cardinalities."""

    experiment = ExperimentParameters(
        number_of_sensors=3,
        connectivity_counts=(3, 0, 0),
    )

    with pytest.raises(ValueError, match="cardinalities"):
        build_environment(
            experiment,
            explicit_connectivity_sets={1: (1, 2), 2: (3,), 3: ()},
        )

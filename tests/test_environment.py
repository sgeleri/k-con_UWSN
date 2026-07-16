"""Tests for the Section III-A network environment."""

import numpy as np
import pytest

from kcon_uwsn.environment import (
    Deployment,
    NetworkEnvironment,
    build_directed_arcs,
    build_network_environment,
    build_paper_network_environment,
    generate_uniform_deployment,
    pairwise_distances,
)
from kcon_uwsn.params import ExperimentParameters


def _experiment(
    *,
    number_of_sensors: int = 4,
    volume_km: tuple[float, float, float] = (1.0, 2.0, 0.3),
    seed: int = 7,
) -> ExperimentParameters:
    return ExperimentParameters(
        number_of_sensors=number_of_sensors,
        volume_km=volume_km,
        connectivity_counts=(number_of_sensors, 0, 0),
        random_seed=seed,
    )


def test_uniform_deployment_is_reproducible_and_uses_corner_bs() -> None:
    """Paper: Section III-A; implementation choice fixes seed and coordinates."""

    experiment = _experiment()
    first = generate_uniform_deployment(experiment)
    second = generate_uniform_deployment(experiment)

    np.testing.assert_array_equal(first.positions_m, second.positions_m)
    np.testing.assert_array_equal(first.positions_m[0], (-500.0, 0.0, 0.0))
    assert first.bs_index == 0
    assert first.nodes == (0, 1, 2, 3, 4)
    assert first.sensors == (1, 2, 3, 4)


def test_uniform_sensors_stay_inside_rectangular_prism() -> None:
    """Paper: Section III-A and Fig. 1."""

    deployment = generate_uniform_deployment(_experiment())
    sensors = deployment.positions_m[1:]

    assert np.all((-500.0 <= sensors[:, 0]) & (sensors[:, 0] <= 500.0))
    assert np.all((0.0 <= sensors[:, 1]) & (sensors[:, 1] <= 2000.0))
    assert np.all((-300.0 <= sensors[:, 2]) & (sensors[:, 2] <= 0.0))


def test_two_dimensional_deployment_places_every_node_at_zero_depth() -> None:
    """Paper: Section IV-B treats a 1x1 km 2D cross section."""

    experiment = _experiment(volume_km=(1.0, 1.0, 0.3))
    deployment = generate_uniform_deployment(experiment, two_dimensional=True)

    np.testing.assert_array_equal(deployment.positions_m[:, 2], 0.0)
    np.testing.assert_array_equal(deployment.positions_m[0], (-500.0, 0.0, 0.0))


def test_deployment_owns_immutable_position_data() -> None:
    """Implementation decision: environment data cannot mutate during a solve."""

    source = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]])
    deployment = Deployment(source)
    source[1, 0] = 99.0

    assert deployment.positions_m[1, 0] == 1.0
    with pytest.raises(ValueError):
        deployment.positions_m[1, 0] = 2.0


def test_pairwise_distances_are_euclidean_symmetric_and_zero_diagonal() -> None:
    """Paper: Section III-A defines d_ij as inter-node distance."""

    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [3.0, 4.0, 0.0],
            [0.0, 0.0, 12.0],
        ]
    )
    distances = pairwise_distances(positions)

    assert distances[0, 1] == pytest.approx(5.0)
    assert distances[0, 2] == pytest.approx(12.0)
    assert distances[1, 2] == pytest.approx(13.0)
    np.testing.assert_allclose(distances, distances.T)
    np.testing.assert_array_equal(np.diag(distances), 0.0)


def test_directed_arcs_include_range_boundary_and_exclude_self_loops() -> None:
    """Paper: Section III-A uses d_ij <= R_max(l_max)."""

    positions = np.array(
        [
            [0.0, 0.0, 0.0],
            [1000.0, 0.0, 0.0],
            [0.0, 1000.1, 0.0],
        ]
    )
    distances = pairwise_distances(positions)
    arcs = build_directed_arcs(distances, maximum_transmission_range_m=1000.0)

    assert arcs == ((0, 1), (1, 0))
    assert all(source != target for source, target in arcs)
    assert 2 not in {endpoint for arc in arcs for endpoint in arc}


def test_network_environment_exposes_paper_sets_and_read_only_distances() -> None:
    """Paper: Section III-A defines G=(V,A) and W as the sensors."""

    deployment = Deployment(
        np.array(
            [
                [0.0, 0.0, 0.0],
                [100.0, 0.0, 0.0],
                [250.0, 0.0, 0.0],
            ]
        )
    )
    environment = build_network_environment(deployment, 200.0)

    assert environment.nodes == (0, 1, 2)
    assert environment.sensors == (1, 2)
    assert environment.arcs == ((0, 1), (1, 0), (1, 2), (2, 1))
    with pytest.raises(ValueError):
        environment.distances_m[0, 1] = 0.0


def test_paper_network_uses_table_ii_maximum_range() -> None:
    """Paper: Section III-A and Table II set R_max(l_max)=1000 m."""

    environment = build_paper_network_environment(_experiment())

    assert environment.maximum_transmission_range_m == 1000.0
    assert all(
        environment.distances_m[source, target] <= 1000.0
        for source, target in environment.arcs
    )


@pytest.mark.parametrize(
    "positions",
    [
        np.array([0.0, 1.0, 2.0]),
        np.empty((2, 2)),
        np.array([[0.0, 0.0, 0.0], [np.nan, 0.0, 0.0]]),
    ],
)
def test_invalid_deployment_positions_are_rejected(positions: np.ndarray) -> None:
    """Implementation validation for malformed deployment input."""

    with pytest.raises(ValueError):
        Deployment(positions)


def test_network_environment_rejects_arc_beyond_range() -> None:
    """Environment consistency check for the Section III-A arc definition."""

    deployment = Deployment(
        np.array([[0.0, 0.0, 0.0], [20.0, 0.0, 0.0]])
    )
    distances = pairwise_distances(deployment.positions_m)

    with pytest.raises(ValueError, match="exceeds"):
        NetworkEnvironment(
            deployment=deployment,
            distances_m=distances,
            arcs=((0, 1),),
            maximum_transmission_range_m=10.0,
        )

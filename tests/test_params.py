"""Tests for parameters transcribed from Tantur et al. (2025)."""

from dataclasses import FrozenInstanceError

import pytest

from kcon_uwsn.params import (
    AcousticParameters,
    ExperimentParameters,
    NetworkParameters,
    PaperParameters,
    PowerLevelTable,
)


def test_network_parameters_match_table_i() -> None:
    """Paper: Section III-A and Table I."""

    params = NetworkParameters()

    assert params.number_of_rounds == 1440
    assert params.round_duration_s == 300
    assert params.packets_per_sensor_per_round == 1
    assert params.data_packet_size_bits == 1024
    assert params.control_packet_size_bits == 256
    assert params.data_rate_bps == 2500
    assert params.maximum_paths == 5
    assert params.big_m == 10_000
    assert params.interference_range_multiplier == pytest.approx(1.7)
    assert params.control_frequency_range == (0.25, 4.0)
    assert params.connectivity_range == (1, 3)


def test_acoustic_parameters_match_table_i() -> None:
    """Paper: Section III-B, Eqs. (1)-(4), and Table I."""

    params = AcousticParameters()

    assert params.operating_frequency_khz == 25
    assert params.spreading_factor == pytest.approx(1.5)
    assert params.desired_receiver_input_j_per_bit == pytest.approx(1e-7)
    assert params.reception_energy_j_per_bit == pytest.approx(0.2e-7)


def test_power_levels_match_table_ii() -> None:
    """Paper: Section III-B, Eq. (5), and Table II."""

    table = PowerLevelTable()

    assert table.levels == tuple(range(1, 11))
    assert table.ranges_m == tuple(float(value) for value in range(100, 1001, 100))
    assert table.transmission_energy_mj_per_bit == (
        0.115,
        0.375,
        0.792,
        1.404,
        2.258,
        3.416,
        4.954,
        6.967,
        9.568,
        12.897,
    )


def test_table_ii_energy_is_converted_to_joules_per_bit() -> None:
    """Implementation unit decision for the Table II mJ/bit values."""

    table = PowerLevelTable()

    assert table.transmission_energy_j_per_bit[0] == pytest.approx(0.115e-3)
    assert table.transmission_energy_j_per_bit[-1] == pytest.approx(12.897e-3)


def test_default_experiment_matches_figure_1_scale() -> None:
    """Paper: Section III-A, Fig. 1, and Table I."""

    experiment = ExperimentParameters()

    assert experiment.number_of_sensors == 30
    assert experiment.volume_km == (1.0, 3.0, 0.30)
    assert experiment.control_to_data_frequency == 1.0
    assert experiment.connectivity_counts == (30, 0, 0)


@pytest.mark.parametrize(
    ("counts", "number_of_sensors"),
    [
        ((29, 0, 0), 30),
        ((20, 5, 4), 30),
        ((1, -1, 1), 1),
    ],
)
def test_connectivity_partition_counts_are_validated(
    counts: tuple[int, int, int],
    number_of_sensors: int,
) -> None:
    """Paper: Tables III-IV require a disjoint partition of all sensors."""

    with pytest.raises(ValueError):
        ExperimentParameters(
            number_of_sensors=number_of_sensors,
            connectivity_counts=counts,
        )


@pytest.mark.parametrize("xi", [0.24, 4.01])
def test_control_frequency_is_limited_to_paper_range(xi: float) -> None:
    """Paper: Table I gives xi in the range 0.25 through 4."""

    paper = PaperParameters()
    experiment = ExperimentParameters(control_to_data_frequency=xi)

    with pytest.raises(ValueError, match="paper's"):
        paper.validate_experiment(experiment)


def test_parameter_objects_are_immutable() -> None:
    """Implementation decision: paper defaults cannot mutate during a run."""

    params = NetworkParameters()

    with pytest.raises(FrozenInstanceError):
        params.number_of_rounds = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: NetworkParameters(number_of_rounds=0),
        lambda: AcousticParameters(operating_frequency_khz=0),
        lambda: ExperimentParameters(volume_km=(1.0, 0.0, 0.3)),
    ],
)
def test_non_positive_physical_parameters_are_rejected(factory: object) -> None:
    """Implementation validation for physically invalid parameter values."""

    with pytest.raises(ValueError):
        factory()  # type: ignore[operator]

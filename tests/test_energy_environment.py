"""Tests for the Section III-B underwater energy environment."""

import math

import numpy as np
import pytest

from kcon_uwsn.environment import (
    Deployment,
    absorption_coefficient_db_per_km,
    build_acoustic_energy_environment,
    build_network_environment,
    frequency_component,
    minimum_link_transmission_energy_j_per_bit,
    power_level_energies_j_per_bit,
    transmission_energy_j_per_bit,
    transmission_loss,
)
from kcon_uwsn.params import AcousticParameters, PowerLevelTable


def test_absorption_coefficient_matches_equation_2() -> None:
    """Paper: Section III-B, Eq. (2), with f_0=25 kHz."""

    coefficient = absorption_coefficient_db_per_km(25.0)

    assert coefficient == pytest.approx(6.10480510125598)


def test_frequency_component_matches_definition_after_equation_1() -> None:
    """Paper: Section III-B, definition nu=10^(alpha(f_0)/10)."""

    component = frequency_component(6.10480510125598)

    assert component == pytest.approx(4.078312590787304)


def test_transmission_loss_matches_equation_1() -> None:
    """Paper: Section III-B, Eq. (1), for R_max(1)=100 m."""

    loss = transmission_loss(
        distance_m=100.0,
        spreading_factor=1.5,
        frequency_dependent_component=4.078312590787304,
    )

    assert loss == pytest.approx(1150.9277223217633)


def test_transmission_energy_matches_equation_3() -> None:
    """Paper: Section III-B, Eq. (3), E_T(l)=TL(R_max(l))*P_0."""

    energy = transmission_energy_j_per_bit(
        loss=1150.9277223217633,
        desired_receiver_input_j_per_bit=1e-7,
    )

    assert energy == pytest.approx(0.11509277223217632e-3)


def test_calculated_power_levels_match_rounded_table_ii() -> None:
    """Paper: Section III-B, Eqs. (1)-(3), and Table II."""

    table = PowerLevelTable()
    calculated_j_per_bit = power_level_energies_j_per_bit(
        AcousticParameters(),
        table,
    )
    calculated_mj_per_bit = tuple(value * 1e3 for value in calculated_j_per_bit)

    # Table II reports three decimal places. Level 9 differs from the direct
    # equations by 0.00055 mJ/bit, suggesting intermediate rounding in the
    # paper, so one unit in the final published decimal place is allowed.
    assert calculated_mj_per_bit == pytest.approx(
        table.transmission_energy_mj_per_bit,
        abs=0.001,
    )


@pytest.mark.parametrize(
    ("distance_m", "expected_level_index"),
    [
        (0.0, 0),
        (100.0, 0),
        (100.000001, 1),
        (200.0, 1),
        (999.999999, 9),
        (1000.0, 9),
    ],
)
def test_equation_5_selects_minimum_covering_power_level(
    distance_m: float,
    expected_level_index: int,
) -> None:
    """Paper: Section III-B, Eq. (5), including range boundaries."""

    table = PowerLevelTable()
    energies = power_level_energies_j_per_bit(AcousticParameters(), table)

    selected = minimum_link_transmission_energy_j_per_bit(
        distance_m,
        table,
        energies,
    )

    assert selected == energies[expected_level_index]


def test_equation_5_returns_infinity_beyond_maximum_range() -> None:
    """Paper: Section III-B, Eq. (5), d_ij>R_max(10)."""

    table = PowerLevelTable()
    energies = power_level_energies_j_per_bit(AcousticParameters(), table)

    selected = minimum_link_transmission_energy_j_per_bit(
        1000.000001,
        table,
        energies,
    )

    assert math.isinf(selected)


def test_energy_environment_assigns_per_arc_energy_and_reception_cost() -> None:
    """Paper: Section III-B, Eqs. (4)-(5)."""

    deployment = Deployment(
        np.array(
            [
                [0.0, 0.0, 0.0],
                [50.0, 0.0, 0.0],
                [250.0, 0.0, 0.0],
            ]
        )
    )
    network = build_network_environment(deployment, 1000.0)
    energy_environment = build_acoustic_energy_environment(network)
    level_energies = energy_environment.transmission_energy_by_level_j_per_bit

    assert energy_environment.reception_energy_j_per_bit == pytest.approx(0.2e-7)
    assert energy_environment.link_transmission_energy_j_per_bit[(0, 1)] == (
        level_energies[0]
    )
    assert energy_environment.link_transmission_energy_j_per_bit[(0, 2)] == (
        level_energies[2]
    )
    assert energy_environment.link_transmission_energy_j_per_bit[(1, 2)] == (
        level_energies[1]
    )


def test_per_arc_energy_mapping_is_immutable() -> None:
    """Implementation decision: MILP coefficients cannot mutate after build."""

    deployment = Deployment(np.array([[0.0, 0.0, 0.0], [50.0, 0.0, 0.0]]))
    network = build_network_environment(deployment, 1000.0)
    energy_environment = build_acoustic_energy_environment(network)

    with pytest.raises(TypeError):
        energy_environment.link_transmission_energy_j_per_bit[(0, 1)] = 0.0


@pytest.mark.parametrize(
    ("function", "arguments"),
    [
        (absorption_coefficient_db_per_km, (0.0,)),
        (frequency_component, (-1.0,)),
        (transmission_loss, (0.0, 1.5, 4.0)),
        (transmission_energy_j_per_bit, (1.0, 0.0)),
    ],
)
def test_invalid_acoustic_inputs_are_rejected(
    function: object,
    arguments: tuple[float, ...],
) -> None:
    """Implementation validation for Eqs. (1)-(3)."""

    with pytest.raises(ValueError):
        function(*arguments)  # type: ignore[operator]

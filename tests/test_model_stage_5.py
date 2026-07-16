"""Structural tests for Stage 5 MILP variables, domains, and objective."""

import pulp
import pytest

from kcon_uwsn.environment import build_environment
from kcon_uwsn.model import ModelVars, build_model
from kcon_uwsn.params import ExperimentParameters


@pytest.fixture
def stage_5_model() -> tuple[pulp.LpProblem, ModelVars]:
    experiment = ExperimentParameters(
        number_of_sensors=2,
        volume_km=(0.1, 0.1, 0.1),
        connectivity_counts=(2, 0, 0),
        random_seed=3,
    )
    environment = build_environment(experiment, two_dimensional=True)
    return build_model(environment)


def test_variable_index_counts_match_section_iii_c(
    stage_5_model: tuple[pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Section III-C variable definitions with N_l=5."""

    problem, variables = stage_5_model
    number_of_flow_keys = 2 * 5 * 6
    number_of_path_keys = 2 * 5

    assert len(variables.data_flow) == number_of_flow_keys
    assert len(variables.control_flow) == number_of_flow_keys
    assert len(variables.arc_used) == number_of_flow_keys
    assert len(variables.path_packets) == number_of_path_keys
    # PuLP 3.3 registers variables lazily when objective/constraint expressions
    # use them. At Stage 5 only epsilon appears in an expression.
    assert len(problem.variables()) == 1


def test_flow_keys_use_one_based_path_and_zero_based_node_indices(
    stage_5_model: tuple[pulp.LpProblem, ModelVars],
) -> None:
    """Paper paths are one-based; zero-based nodes are an implementation choice."""

    _, variables = stage_5_model

    assert (1, 1, 0, 1) in variables.data_flow
    assert (2, 5, 2, 0) in variables.data_flow
    assert all(key[1] in range(1, 6) for key in variables.data_flow)
    assert (1, 0, 0, 1) not in variables.data_flow


def test_f_and_g_domains_match_constraint_23(
    stage_5_model: tuple[pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Constraint (23), f and g are non-negative integers."""

    _, variables = stage_5_model

    for variable in (
        next(iter(variables.data_flow.values())),
        next(iter(variables.control_flow.values())),
    ):
        assert variable.cat == pulp.LpInteger
        assert variable.lowBound == 0
        assert variable.upBound is None


def test_h_domain_matches_constraint_24(
    stage_5_model: tuple[pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Constraint (24), h is binary."""

    _, variables = stage_5_model
    variable = next(iter(variables.arc_used.values()))

    assert variable.isBinary()
    assert variable.lowBound == 0
    assert variable.upBound == 1


def test_p_domain_matches_constraint_25(
    stage_5_model: tuple[pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Constraint (25), p is a non-negative integer."""

    _, variables = stage_5_model
    variable = next(iter(variables.path_packets.values()))

    assert variable.cat == pulp.LpInteger
    assert variable.lowBound == 0
    assert variable.upBound is None


def test_epsilon_and_objective_match_equation_6(
    stage_5_model: tuple[pulp.LpProblem, ModelVars],
) -> None:
    """Paper: Objective (6), minimize continuous epsilon."""

    problem, variables = stage_5_model
    epsilon = variables.maximum_sensor_energy

    assert epsilon.cat == pulp.LpContinuous
    assert epsilon.lowBound == 0
    assert problem.sense == pulp.LpMinimize
    assert problem.objective.get(epsilon) == 1
    assert problem.numConstraints() == 0


def test_variable_mappings_are_immutable(
    stage_5_model: tuple[pulp.LpProblem, ModelVars],
) -> None:
    """Implementation decision: ModelVars index maps cannot be replaced."""

    _, variables = stage_5_model

    with pytest.raises(TypeError):
        variables.path_packets[(1, 1)] = variables.path_packets[(1, 2)]


def test_highs_backend_is_available() -> None:
    """Implementation stack decision for the later runner."""

    assert pulp.HiGHS().available()

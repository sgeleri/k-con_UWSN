"""Tests for Stage 11 solver-independent solution extraction."""

import pulp
import pytest

from kcon_uwsn.environment import EnvironmentData, build_environment
from kcon_uwsn.model import ModelVars, build_model
from kcon_uwsn.params import ExperimentParameters
from kcon_uwsn.solution import Solution, _ordered_path, extract_solution


@pytest.fixture(scope="module")
def solved_case() -> tuple[EnvironmentData, ModelVars, Solution]:
    experiment = ExperimentParameters(
        number_of_sensors=2,
        volume_km=(0.1, 0.1, 0.1),
        connectivity_counts=(0, 2, 0),
        random_seed=9,
    )
    environment = build_environment(experiment, two_dimensional=True)
    problem, variables = build_model(environment)
    status = problem.solve(pulp.HiGHS(msg=False))
    assert pulp.LpStatus[status] == "Optimal"
    return (
        environment,
        variables,
        extract_solution(
            problem,
            variables,
            environment,
        ),
    )


def test_unsolved_problem_returns_status_without_values() -> None:
    """Stage 11 runner support for a model with no incumbent."""

    experiment = ExperimentParameters(
        number_of_sensors=2,
        volume_km=(0.1, 0.1, 0.1),
        connectivity_counts=(2, 0, 0),
    )
    environment = build_environment(experiment, two_dimensional=True)
    problem, variables = build_model(environment)

    solution = extract_solution(problem, variables, environment)

    assert solution.status == "No Solution"
    assert solution.pulp_status == "Not Solved"
    assert not solution.has_incumbent
    assert solution.objective_energy_j is None
    assert solution.paths == {}


def test_relaxation_values_without_integer_incumbent_are_not_extracted() -> None:
    """Regression: CBC may populate relaxation values after no feasible MIP."""

    experiment = ExperimentParameters(
        number_of_sensors=2,
        volume_km=(0.1, 0.1, 0.1),
        connectivity_counts=(2, 0, 0),
    )
    environment = build_environment(experiment, two_dimensional=True)
    problem, variables = build_model(environment)
    variables.maximum_sensor_energy.varValue = 123.0
    problem.status = pulp.LpStatusNotSolved
    problem.sol_status = pulp.LpSolutionNoSolutionFound

    solution = extract_solution(problem, variables, environment)

    assert not solution.has_incumbent
    assert solution.objective_energy_j is None


def test_integer_feasible_status_is_not_reported_as_optimal() -> None:
    """Regression: a limit-reached incumbent is feasible, not proven optimal."""

    experiment = ExperimentParameters(
        number_of_sensors=2,
        volume_km=(0.1, 0.1, 0.1),
        connectivity_counts=(2, 0, 0),
    )
    environment = build_environment(experiment, two_dimensional=True)
    problem, variables = build_model(environment)
    problem.solve(pulp.HiGHS(msg=False))
    problem.sol_status = pulp.LpSolutionIntegerFeasible

    solution = extract_solution(problem, variables, environment)

    assert solution.status == "Feasible"
    assert solution.has_incumbent
    assert solution.pulp_solution_status == "Solution Found"


def test_path_extraction_reports_disconnected_extraneous_cycle() -> None:
    path, extraneous = _ordered_path(
        source=1,
        bs_index=0,
        active_arcs=((1, 2), (2, 0), (3, 4), (4, 3)),
    )

    assert path == ((1, 2), (2, 0))
    assert extraneous == ((3, 4), (4, 3))


def test_solution_exposes_status_objective_and_sparse_values(
    solved_case: tuple[EnvironmentData, ModelVars, Solution],
) -> None:
    """Paper: Objective (6) and Section III-C decision variables."""

    _, _, solution = solved_case

    assert solution.status == "Optimal"
    assert solution.has_incumbent
    assert solution.objective_energy_j is not None
    assert solution.objective_energy_j > 0
    assert all(value > 0 for value in solution.data_flow_packets.values())
    assert all(value > 0 for value in solution.control_flow_packets.values())
    assert all(value == 1 for value in solution.active_arcs.values())
    assert all(value > 0 for value in solution.path_packets.values())


def test_reconstructed_paths_are_contiguous_source_to_bs(
    solved_case: tuple[EnvironmentData, ModelVars, Solution],
) -> None:
    """Paper: Constraints (12)–(20)."""

    environment, _, solution = solved_case

    for (source, _), arcs in solution.paths.items():
        assert arcs[0][0] == source
        assert arcs[-1][1] == environment.network.bs_index
        assert all(
            first[1] == second[0] for first, second in zip(arcs, arcs[1:], strict=False)
        )
        assert len({node for arc in arcs for node in arc}) == len(arcs) + 1


def test_path_counts_and_packet_balance_satisfy_constraints_8_and_18(
    solved_case: tuple[EnvironmentData, ModelVars, Solution],
) -> None:
    """Paper: Constraints (8) and (18)."""

    environment, _, solution = solved_case

    for source in environment.network.sensors:
        assert solution.active_path_count_by_source[source] >= 2
        assert solution.connectivity_shortfall_by_source[source] == 0
        assert solution.packet_balance_error_by_source[source] <= 1e-7


def test_energy_diagnostics_match_objective_and_constraint_21(
    solved_case: tuple[EnvironmentData, ModelVars, Solution],
) -> None:
    """Paper: Constraint (21) and Objective (6)."""

    environment, _, solution = solved_case
    assert solution.objective_energy_j is not None

    assert set(solution.node_energy_j) == set(environment.network.sensors)
    assert max(solution.node_energy_j.values()) == pytest.approx(
        solution.objective_energy_j,
        rel=1e-8,
        abs=1e-7,
    )
    assert solution.maximum_energy_violation_j <= 1e-7


def test_airtime_diagnostics_satisfy_constraint_22(
    solved_case: tuple[EnvironmentData, ModelVars, Solution],
) -> None:
    """Paper: Constraint (22), using the documented A\\{i} interpretation."""

    environment, _, solution = solved_case
    available_time = (
        environment.paper.network.number_of_rounds
        * environment.paper.network.round_duration_s
    )

    assert set(solution.node_airtime_s) == set(environment.network.nodes)
    assert all(
        value <= available_time + 1e-7 for value in solution.node_airtime_s.values()
    )
    assert solution.maximum_airtime_violation_s <= 1e-7


def test_solution_mappings_are_immutable(
    solved_case: tuple[EnvironmentData, ModelVars, Solution],
) -> None:
    """Implementation decision: extracted results are stable diagnostics."""

    _, _, solution = solved_case
    source = next(iter(solution.active_path_count_by_source))

    with pytest.raises(TypeError):
        solution.active_path_count_by_source[source] = 0


def test_extraction_rejects_non_positive_tolerance() -> None:
    """Implementation validation for numerical extraction settings."""

    experiment = ExperimentParameters(
        number_of_sensors=2,
        volume_km=(0.1, 0.1, 0.1),
        connectivity_counts=(2, 0, 0),
    )
    environment = build_environment(experiment, two_dimensional=True)
    problem, variables = build_model(environment)

    with pytest.raises(ValueError, match="tolerance"):
        extract_solution(problem, variables, environment, tolerance=0)

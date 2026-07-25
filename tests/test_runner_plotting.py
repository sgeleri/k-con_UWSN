"""Tests for Stage 12 runner and Stage 13 Fig. 3 rendering."""

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

import matplotlib
import pulp
import pytest

matplotlib.use("Agg")

from kcon_uwsn.environment import build_environment
from kcon_uwsn.params import (
    ExperimentParameters,
    NetworkParameters,
    PaperParameters,
)
from kcon_uwsn.plotting import save_figure_3_outputs, save_scenario_outputs
from kcon_uwsn.run import (
    _solution_exit_code,
    main,
    run_approximate_figure_3,
    scenario_i_experiment,
    solve_experiment,
)


@pytest.fixture(scope="module")
def small_run():
    experiment = ExperimentParameters(
        number_of_sensors=2,
        volume_km=(0.1, 0.1, 0.1),
        connectivity_counts=(2, 0, 0),
        random_seed=11,
    )
    return solve_experiment(
        experiment,
        two_dimensional=True,
        time_limit_s=10.0,
        mip_gap=0.0,
    )


def test_solve_experiment_runs_complete_pipeline(small_run) -> None:
    """Stage 12: environment -> model -> HiGHS -> Solution."""

    assert small_run.solution.status == "Optimal"
    assert small_run.solution.has_incumbent
    assert small_run.solution.objective_energy_j is not None
    assert small_run.wall_time_s >= 0


@pytest.mark.parametrize(
    ("time_limit", "mip_gap"),
    [(0.0, 0.01), (1.0, -0.01), (1.0, 1.0)],
)
def test_runner_rejects_invalid_solver_options(
    time_limit: float,
    mip_gap: float,
) -> None:
    experiment = ExperimentParameters(
        number_of_sensors=2,
        connectivity_counts=(2, 0, 0),
    )

    with pytest.raises(ValueError):
        solve_experiment(
            experiment,
            time_limit_s=time_limit,
            mip_gap=mip_gap,
        )


def test_scenario_i_configuration_matches_section_iv_b_table_iii() -> None:
    """Paper: Section IV-B and Table III Scenario-I."""

    experiment = scenario_i_experiment(seed=7)

    assert experiment.number_of_sensors == 12
    assert experiment.volume_km == (1.0, 1.0, 0.30)
    assert experiment.connectivity_counts == (12, 0, 0)
    assert experiment.control_to_data_frequency == 1.0
    assert experiment.random_seed == 7


def test_cli_small_case_reports_solution(capsys) -> None:
    exit_code = main(
        [
            "--sensors",
            "2",
            "--volume-km",
            "0.1",
            "0.1",
            "0.1",
            "--connectivity-counts",
            "2",
            "0",
            "0",
            "--two-dimensional",
            "--time-limit",
            "10",
            "--mip-gap",
            "0",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Status: Optimal" in output
    assert "epsilon:" in output
    assert "Active paths:" in output


def test_feasible_unproven_incumbent_uses_distinct_exit_code(small_run) -> None:
    feasible = replace(small_run.solution, status="Feasible")

    assert _solution_exit_code(feasible) == 3
    assert _solution_exit_code(small_run.solution) == 0


def test_figure_outputs_and_metadata_are_created(
    small_run,
    tmp_path: Path,
) -> None:
    paths = save_scenario_outputs(
        small_run.environment,
        small_run.solution,
        tmp_path,
    )

    assert set(paths) == {"figure_3a", "figure_3b", "figure_3ab", "metadata"}
    assert all(path.exists() and path.stat().st_size > 0 for path in paths.values())

    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    assert metadata["paper_reference"] is None
    assert "does not publish" in metadata["reproduction_note"]
    assert len(metadata["positions_m"]) == 3
    assert metadata["status"] == "Optimal"
    assert metadata["software_versions"]["pulp"] == pulp.__version__
    assert set(metadata["artifact_sha256"]) == {
        "figure_3a",
        "figure_3b",
        "figure_3ab",
    }


def test_topology_figure_is_deterministic(small_run, tmp_path: Path) -> None:
    first = save_scenario_outputs(
        small_run.environment,
        small_run.solution,
        tmp_path / "first",
    )
    second = save_scenario_outputs(
        small_run.environment,
        small_run.solution,
        tmp_path / "second",
    )

    first_hash = hashlib.sha256(first["figure_3a"].read_bytes()).digest()
    second_hash = hashlib.sha256(second["figure_3a"].read_bytes()).digest()
    assert first_hash == second_hash


def test_figure_3_writer_rejects_non_paper_scale_fixture(
    small_run,
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="12 sensor"):
        save_figure_3_outputs(
            small_run.environment,
            small_run.solution,
            tmp_path,
        )


def test_paper_labeled_figure_writer_rejects_n_l_2(
    small_run,
    tmp_path: Path,
) -> None:
    environment = build_environment(
        scenario_i_experiment(),
        paper=PaperParameters(
            network=NetworkParameters(
                maximum_paths=2,
                connectivity_range=(1, 2),
            )
        ),
        explicit_connectivity_sets={1: tuple(range(1, 13)), 2: ()},
        two_dimensional=True,
    )

    with pytest.raises(ValueError, match="N_l=5"):
        save_figure_3_outputs(environment, small_run.solution, tmp_path)


def test_cli_rejects_zero_time_limit() -> None:
    with pytest.raises(ValueError, match="time_limit_s"):
        main(["--time-limit", "0"])
    with pytest.raises(ValueError, match="time_limit_s"):
        main(["--figure-3", "--time-limit", "0"])


@pytest.mark.skipif(
    not pulp.COIN_CMD(
        path=pulp.PULP_CBC_CMD.pulp_cbc_path,
        msg=False,
    ).available(),
    reason="CBC executable is unavailable",
)
def test_short_time_limited_cbc_run_does_not_crash_extraction() -> None:
    experiment = ExperimentParameters(
        number_of_sensors=4,
        volume_km=(0.2, 0.2, 0.1),
        connectivity_counts=(4, 0, 0),
    )

    result = solve_experiment(
        experiment,
        two_dimensional=True,
        time_limit_s=0.001,
        solver_name="cbc",
    )

    assert result.solution.status in {
        "Optimal",
        "Optimal within solver tolerance",
        "Feasible",
        "No Solution",
        "Invalid Incumbent",
    }


@pytest.mark.slow
@pytest.mark.skipif(
    os.environ.get("RUN_SLOW_FIGURE_TEST") != "1",
    reason="set RUN_SLOW_FIGURE_TEST=1 to run the full Figure 3 solve",
)
def test_approximate_figure_3_workflow_end_to_end(tmp_path: Path) -> None:
    result, paths = run_approximate_figure_3(
        tmp_path,
        seed=42,
        threads=1,
        time_limit_s=45.0,
        mip_gap=0.15,
    )

    assert result.solution.has_incumbent
    assert set(paths) == {"figure_3a", "figure_3b", "figure_3ab", "metadata"}
    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    assert len(metadata["positions_m"]) == 13
    assert metadata["random_seed"] == 42
    assert metadata["maximum_paths"] == 2
    assert metadata["artifact_kind"] == "explicit-n_l-2-approximation"
    assert metadata["connectivity_counts"] == [12, 0, 0]
    assert metadata["run_configuration"]["threads"] == 1

"""Tests for Stage 12 runner and Stage 13 Fig. 3 rendering."""

import hashlib
import json
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")

from kcon_uwsn.params import ExperimentParameters
from kcon_uwsn.plotting import save_figure_3_outputs
from kcon_uwsn.run import main, scenario_i_experiment, solve_experiment


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


def test_figure_outputs_and_metadata_are_created(
    small_run,
    tmp_path: Path,
) -> None:
    paths = save_figure_3_outputs(
        small_run.environment,
        small_run.solution,
        tmp_path,
    )

    assert set(paths) == {"figure_3a", "figure_3b", "figure_3ab", "metadata"}
    assert all(path.exists() and path.stat().st_size > 0 for path in paths.values())

    metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
    assert metadata["paper_reference"].startswith("Section IV-B")
    assert "does not publish" in metadata["reproduction_note"]
    assert len(metadata["positions_m"]) == 3
    assert metadata["status"] == "Optimal"


def test_topology_figure_is_deterministic(small_run, tmp_path: Path) -> None:
    first = save_figure_3_outputs(
        small_run.environment,
        small_run.solution,
        tmp_path / "first",
    )
    second = save_figure_3_outputs(
        small_run.environment,
        small_run.solution,
        tmp_path / "second",
    )

    first_hash = hashlib.sha256(first["figure_3a"].read_bytes()).digest()
    second_hash = hashlib.sha256(second["figure_3a"].read_bytes()).digest()
    assert first_hash == second_hash

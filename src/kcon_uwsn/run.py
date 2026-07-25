"""Stage 12 wrapper and command-line entry point for paper experiments."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pulp

from .environment import EnvironmentData, build_environment
from .model import build_model
from .params import ExperimentParameters, NetworkParameters, PaperParameters
from .solution import Solution, extract_solution

SolverName = Literal["highs", "cbc"]


@dataclass(frozen=True, slots=True)
class RunResult:
    """Environment, extracted solution, and measured end-to-end solve time."""

    environment: EnvironmentData
    solution: Solution
    wall_time_s: float
    solver_name: SolverName
    time_limit_s: float
    requested_mip_gap: float
    threads: int | None


def solve_experiment(
    experiment: ExperimentParameters,
    *,
    paper: PaperParameters | None = None,
    explicit_connectivity_sets: Mapping[int, tuple[int, ...]] | None = None,
    two_dimensional: bool = False,
    time_limit_s: float = 60.0,
    mip_gap: float = 0.01,
    threads: int | None = None,
    solver_name: SolverName = "highs",
    solver_log: bool = False,
) -> RunResult:
    """Build the environment/model, solve with HiGHS, and extract results."""

    if time_limit_s <= 0:
        raise ValueError("time_limit_s must be positive")
    if not 0 <= mip_gap < 1:
        raise ValueError("mip_gap must satisfy 0 <= mip_gap < 1")
    if threads is not None and threads <= 0:
        raise ValueError("threads must be positive")
    if solver_name not in ("highs", "cbc"):
        raise ValueError("solver_name must be 'highs' or 'cbc'")

    environment = build_environment(
        experiment,
        paper=paper,
        explicit_connectivity_sets=explicit_connectivity_sets,
        two_dimensional=two_dimensional,
    )
    problem, variables = build_model(environment)
    if solver_name == "highs":
        solver: pulp.LpSolver = pulp.HiGHS(
            msg=solver_log,
            timeLimit=time_limit_s,
            gapRel=mip_gap,
            threads=threads,
        )
    else:
        solver = pulp.COIN_CMD(
            path=pulp.PULP_CBC_CMD.pulp_cbc_path,
            msg=solver_log,
            timeLimit=time_limit_s,
            gapRel=mip_gap,
            threads=threads,
        )

    started = time.perf_counter()
    problem.solve(solver)
    wall_time_s = time.perf_counter() - started
    solution = extract_solution(problem, variables, environment)

    return RunResult(
        environment=environment,
        solution=solution,
        wall_time_s=wall_time_s,
        solver_name=solver_name,
        time_limit_s=time_limit_s,
        requested_mip_gap=mip_gap,
        threads=threads,
    )


def scenario_i_experiment(seed: int = 42) -> ExperimentParameters:
    """Return the Section IV-B / Table III Scenario-I configuration."""

    # Paper: Section IV-B and Table III, Scenario-I.
    return ExperimentParameters(
        number_of_sensors=12,
        volume_km=(1.0, 1.0, 0.30),
        control_to_data_frequency=1.0,
        connectivity_counts=(12, 0, 0),
        random_seed=seed,
    )


def _run_figure_3_variant(
    output_directory: Path,
    *,
    seed: int,
    time_limit_s: float,
    mip_gap: float,
    threads: int | None,
    solver_name: SolverName,
    maximum_paths: int,
    solver_log: bool,
    approximate: bool,
) -> tuple[RunResult, Mapping[str, Path]]:
    """Solve one validated Scenario-I figure variant."""

    if maximum_paths < 2:
        raise ValueError("Scenario-I figure generation requires at least 2 paths")
    figure_paper = PaperParameters(
        network=NetworkParameters(
            maximum_paths=maximum_paths,
            connectivity_range=(1, min(3, maximum_paths)),
        )
    )
    result = solve_experiment(
        scenario_i_experiment(seed),
        paper=figure_paper,
        explicit_connectivity_sets={
            1: tuple(range(1, 13)),
            2: (),
            **({3: ()} if maximum_paths >= 3 else {}),
        },
        two_dimensional=True,
        time_limit_s=time_limit_s,
        mip_gap=mip_gap,
        threads=threads,
        solver_name=solver_name,
        solver_log=solver_log,
    )
    if not result.solution.has_incumbent:
        return result, {}

    from .plotting import (
        save_approximate_figure_3_outputs,
        save_figure_3_outputs,
    )

    writer = save_approximate_figure_3_outputs if approximate else save_figure_3_outputs
    paths = writer(
        result.environment,
        result.solution,
        output_directory,
        run_metadata={
            "solver_name": result.solver_name,
            "time_limit_s": result.time_limit_s,
            "requested_mip_gap": result.requested_mip_gap,
            "threads": result.threads,
            "wall_time_s": result.wall_time_s,
        },
    )
    return result, paths


def run_figure_3(
    output_directory: Path,
    *,
    seed: int = 42,
    time_limit_s: float = 60.0,
    mip_gap: float = 0.01,
    threads: int | None = 1,
    solver_name: SolverName = "highs",
    solver_log: bool = False,
) -> tuple[RunResult, Mapping[str, Path]]:
    """Run Scenario-I with the paper's Table I N_l=5 model."""

    return _run_figure_3_variant(
        output_directory,
        seed=seed,
        time_limit_s=time_limit_s,
        mip_gap=mip_gap,
        threads=threads,
        solver_name=solver_name,
        maximum_paths=5,
        solver_log=solver_log,
        approximate=False,
    )


def run_approximate_figure_3(
    output_directory: Path,
    *,
    seed: int = 42,
    time_limit_s: float = 45.0,
    mip_gap: float = 0.15,
    threads: int | None = 1,
    solver_name: SolverName = "highs",
    solver_log: bool = False,
) -> tuple[RunResult, Mapping[str, Path]]:
    """Run the explicitly labeled tractable N_l=2 approximation."""

    return _run_figure_3_variant(
        output_directory,
        seed=seed,
        time_limit_s=time_limit_s,
        mip_gap=mip_gap,
        threads=threads,
        solver_name=solver_name,
        maximum_paths=2,
        solver_log=solver_log,
        approximate=True,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Solve the Tantur 2025 non-uniform k-connectivity MILP.",
    )
    parser.add_argument("--sensors", type=int, default=4)
    parser.add_argument(
        "--volume-km",
        type=float,
        nargs=3,
        metavar=("DX", "DY", "DZ"),
        default=(0.2, 0.2, 0.1),
    )
    parser.add_argument(
        "--connectivity-counts",
        type=int,
        nargs=3,
        metavar=("N1", "N2", "N3"),
        default=None,
    )
    parser.add_argument("--xi", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--two-dimensional", action="store_true")
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--mip-gap", type=float, default=None)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--solver", choices=("highs", "cbc"), default=None)
    parser.add_argument("--solver-log", action="store_true")
    parser.add_argument(
        "--figure-3",
        action="store_true",
        help="Run Scenario-I with the paper's Table I N_l=5 model.",
    )
    parser.add_argument(
        "--approximate-figure-3",
        action="store_true",
        help="Run an explicitly labeled tractable N_l=2 approximation.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    return parser


def _print_summary(result: RunResult) -> None:
    solution = result.solution
    print(f"Status: {solution.status}")
    print(f"Termination: {solution.termination_reason}")
    print(f"Wall time: {result.wall_time_s:.3f} s")
    if not solution.has_incumbent:
        print("No incumbent solution is available.")
        return

    assert solution.objective_energy_j is not None
    print(f"epsilon: {solution.objective_energy_j / 1000.0:.6f} kJ")
    if solution.relative_gap is not None:
        print(f"Relative MIP gap: {solution.relative_gap:.4%}")
    print(
        "Active paths: "
        + ", ".join(
            f"node {source}={count}"
            for source, count in solution.active_path_count_by_source.items()
        )
    )
    print(
        "Maximum residuals: "
        f"energy={solution.maximum_energy_violation_j:.3e} J, "
        f"airtime={solution.maximum_airtime_violation_s:.3e} s"
    )


def _solution_exit_code(solution: Solution) -> int:
    if solution.status.startswith("Optimal"):
        return 0
    if solution.has_incumbent:
        return 3
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run a small experiment or the Fig. 3(a)/(b) workflow."""

    arguments = _build_parser().parse_args(argv)
    if arguments.figure_3 and arguments.approximate_figure_3:
        raise ValueError("select only one Figure-3 workflow")
    if arguments.figure_3 or arguments.approximate_figure_3:
        approximate = arguments.approximate_figure_3
        runner = run_approximate_figure_3 if approximate else run_figure_3
        result, paths = runner(
            arguments.output_dir,
            seed=arguments.seed,
            time_limit_s=(
                (45.0 if approximate else 60.0)
                if arguments.time_limit is None
                else arguments.time_limit
            ),
            mip_gap=(
                (0.15 if approximate else 0.01)
                if arguments.mip_gap is None
                else arguments.mip_gap
            ),
            threads=1 if arguments.threads is None else arguments.threads,
            solver_name=arguments.solver or "highs",
            solver_log=arguments.solver_log,
        )
        _print_summary(result)
        for label, path in paths.items():
            print(f"{label}: {path}")
        return _solution_exit_code(result.solution)

    counts = arguments.connectivity_counts
    if counts is None:
        counts = (arguments.sensors, 0, 0)
    experiment = ExperimentParameters(
        number_of_sensors=arguments.sensors,
        volume_km=tuple(arguments.volume_km),
        control_to_data_frequency=arguments.xi,
        connectivity_counts=tuple(counts),
        random_seed=arguments.seed,
    )
    result = solve_experiment(
        experiment,
        two_dimensional=arguments.two_dimensional,
        time_limit_s=60.0 if arguments.time_limit is None else arguments.time_limit,
        mip_gap=0.01 if arguments.mip_gap is None else arguments.mip_gap,
        threads=arguments.threads,
        solver_name=arguments.solver or "highs",
        solver_log=arguments.solver_log,
    )
    _print_summary(result)
    return _solution_exit_code(result.solution)


if __name__ == "__main__":
    sys.exit(main())

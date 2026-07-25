"""Stage 13 rendering for Section IV-B Fig. 3(a) and Fig. 3(b)."""

from __future__ import annotations

import json
import platform
import sys
from collections import defaultdict
from collections.abc import Mapping
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .environment import DirectedArc, EnvironmentData
from .solution import Solution

_PATH_COLORS = ("tab:blue", "tab:red", "tab:green", "tab:orange", "tab:purple")
_REPRODUCTION_NOTE = (
    "Methodological reproduction: the paper does not publish the 12 sensor "
    "coordinates or random seed, so the generated topology is deterministic "
    "but not claimed to be numerically or pixel-identical to Fig. 3."
)


def _new_axes() -> tuple[Figure, Axes]:
    return plt.subplots(figsize=(7.0, 6.0), constrained_layout=True)


def _positions_km(env: EnvironmentData) -> np.ndarray:
    return env.network.deployment.positions_m / 1000.0


def _format_topology_axes(ax: Axes, env: EnvironmentData) -> None:
    dx, dy, _ = env.experiment.volume_km
    ax.set_xlim(-dx / 2.0 - 0.03 * dx, dx / 2.0 + 0.03 * dx)
    ax.set_ylim(-0.03 * dy, dy + 0.03 * dy)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.grid(alpha=0.2)


def _draw_bs_and_labels(ax: Axes, env: EnvironmentData) -> None:
    positions = _positions_km(env)
    bs = env.network.bs_index
    ax.scatter(
        positions[bs, 0],
        positions[bs, 1],
        marker="*",
        s=220,
        color="red",
        edgecolor="black",
        linewidth=0.6,
        label="BS",
        zorder=5,
    )
    ax.annotate(
        "BS",
        (positions[bs, 0], positions[bs, 1]),
        xytext=(6, -12),
        textcoords="offset points",
        fontsize=9,
    )
    for sensor in env.network.sensors:
        ax.annotate(
            str(sensor),
            (positions[sensor, 0], positions[sensor, 1]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
            zorder=6,
        )


def plot_network_topology(
    env: EnvironmentData,
    *,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Render the deterministic counterpart of Section IV-B Fig. 3(a)."""

    if ax is None:
        figure, ax = _new_axes()
    else:
        figure = ax.figure

    positions = _positions_km(env)
    sensors = np.asarray(env.network.sensors)
    ax.scatter(
        positions[sensors, 0],
        positions[sensors, 1],
        s=65,
        color="steelblue",
        edgecolor="black",
        linewidth=0.5,
        label="Sensor nodes",
        zorder=4,
    )
    _draw_bs_and_labels(ax, env)
    _format_topology_axes(ax, env)
    ax.set_title("(a) Network Topology")
    ax.legend(loc="upper right", fontsize=8)
    return figure, ax


def _aggregate_data_flow(solution: Solution) -> dict[DirectedArc, float]:
    totals: defaultdict[DirectedArc, float] = defaultdict(float)
    for (_, _, transmitter, receiver), packets in solution.data_flow_packets.items():
        totals[(transmitter, receiver)] += packets
    return dict(totals)


def _draw_individual_flows(
    ax: Axes,
    env: EnvironmentData,
    solution: Solution,
) -> None:
    positions = _positions_km(env)
    for (_, _, transmitter, receiver), packets in solution.data_flow_packets.items():
        if packets <= 0:
            continue
        start = positions[transmitter]
        stop = positions[receiver]
        ax.plot(
            (start[0], stop[0]),
            (start[1], stop[1]),
            color="0.65",
            alpha=0.16,
            linewidth=0.7,
            zorder=1,
        )


def _draw_bottleneck_relay_flow(
    ax: Axes,
    env: EnvironmentData,
    solution: Solution,
    bottleneck: int,
) -> None:
    positions = _positions_km(env)
    totals = {
        arc: packets
        for arc, packets in _aggregate_data_flow(solution).items()
        if bottleneck in arc
    }
    largest_flow = max(totals.values(), default=1.0)
    for (transmitter, receiver), packets in totals.items():
        start = positions[transmitter]
        stop = positions[receiver]
        width = 0.5 + 2.0 * packets / largest_flow
        ax.plot(
            (start[0], stop[0]),
            (start[1], stop[1]),
            linestyle="--",
            color="0.45",
            alpha=0.55,
            linewidth=width,
            zorder=1,
        )


def _draw_bottleneck_paths(
    ax: Axes,
    env: EnvironmentData,
    solution: Solution,
    bottleneck: int,
) -> None:
    positions = _positions_km(env)
    bottleneck_paths = sorted(
        (
            (path, arcs)
            for (source, path), arcs in solution.paths.items()
            if source == bottleneck
        ),
        key=lambda item: item[0],
    )
    for color_index, (path, arcs) in enumerate(bottleneck_paths):
        color = _PATH_COLORS[color_index % len(_PATH_COLORS)]
        for arc_index, (transmitter, receiver) in enumerate(arcs):
            start = positions[transmitter]
            stop = positions[receiver]
            label = f"Node {bottleneck}, path {path}" if arc_index == 0 else None
            ax.plot(
                (start[0], stop[0]),
                (start[1], stop[1]),
                color=color,
                linewidth=2.4,
                label=label,
                zorder=3,
            )


def plot_scenario_i(
    env: EnvironmentData,
    solution: Solution,
    *,
    ax: Axes | None = None,
) -> tuple[Figure, Axes]:
    """Render the methodological counterpart of Section IV-B Fig. 3(b)."""

    if not solution.has_incumbent:
        raise ValueError("Scenario-I plotting requires an incumbent solution")
    if set(env.connectivity.kappa_by_sensor.values()) != {1}:
        raise ValueError("Fig. 3(b) requires Table III Scenario-I (all kappa=1)")

    if ax is None:
        figure, ax = _new_axes()
    else:
        figure = ax.figure

    positions = _positions_km(env)
    sensors = np.asarray(env.network.sensors)
    energy_kj = np.asarray(
        [solution.node_energy_j[sensor] / 1000.0 for sensor in sensors]
    )
    bottleneck = max(solution.node_energy_j, key=solution.node_energy_j.__getitem__)
    _draw_individual_flows(ax, env, solution)
    _draw_bottleneck_relay_flow(ax, env, solution, bottleneck)
    _draw_bottleneck_paths(ax, env, solution, bottleneck)

    sensor_plot = ax.scatter(
        positions[sensors, 0],
        positions[sensors, 1],
        c=energy_kj,
        cmap="viridis",
        s=75,
        edgecolor="black",
        linewidth=0.5,
        zorder=4,
    )
    colorbar = figure.colorbar(sensor_plot, ax=ax, shrink=0.82)
    colorbar.set_label("Sensor energy (kJ)")
    _draw_bs_and_labels(ax, env)
    _format_topology_axes(ax, env)
    assert solution.objective_energy_j is not None
    gap_text = (
        f", gap={solution.relative_gap:.1%}"
        if solution.relative_gap is not None and solution.relative_gap > 1e-7
        else ""
    )
    ax.set_title(
        "(b) Scenario-I\n"
        f"bottleneck=node {bottleneck}, "
        f"epsilon={solution.objective_energy_j / 1000.0:.3f} kJ{gap_text}"
    )
    ax.legend(loc="upper right", fontsize=7)
    return figure, ax


def _package_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def _metadata(
    env: EnvironmentData,
    solution: Solution,
    *,
    run_metadata: Mapping[str, object] | None,
    artifact_paths: Mapping[str, Path],
    paper_reference: str | None,
    artifact_kind: str,
) -> dict[str, object]:
    return {
        "artifact_kind": artifact_kind,
        "paper_reference": paper_reference,
        "reproduction_note": _REPRODUCTION_NOTE,
        "random_seed": env.experiment.random_seed,
        "volume_km": list(env.experiment.volume_km),
        "positions_m": env.network.deployment.positions_m.tolist(),
        "connectivity_counts": list(env.experiment.connectivity_counts),
        "maximum_paths": env.paper.network.maximum_paths,
        "model_deviation": (
            "Approximate workflow uses N_l=2 for open-source solver "
            "tractability instead of Table I N_l=5."
            if env.paper.network.maximum_paths == 2
            else None
        ),
        "status": solution.status,
        "termination_reason": solution.termination_reason,
        "pulp_status": solution.pulp_status,
        "pulp_solution_status": solution.pulp_solution_status,
        "epsilon_j": solution.objective_energy_j,
        "best_bound_j": solution.best_bound_j,
        "relative_gap": solution.relative_gap,
        "software_versions": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "kcon-uwsn": _package_version("kcon-uwsn"),
            "numpy": _package_version("numpy"),
            "matplotlib": _package_version("matplotlib"),
            "pulp": _package_version("pulp"),
            "highspy": _package_version("highspy"),
        },
        "run_configuration": dict(run_metadata or {}),
        "artifact_sha256": {
            label: sha256(path.read_bytes()).hexdigest()
            for label, path in artifact_paths.items()
        },
        "active_path_count_by_source": dict(solution.active_path_count_by_source),
    }


def _save_outputs(
    env: EnvironmentData,
    solution: Solution,
    output_directory: Path,
    *,
    run_metadata: Mapping[str, object] | None = None,
    figure_3: bool,
    approximate: bool = False,
) -> Mapping[str, Path]:
    """Save generic topology/scenario images and reproducibility metadata."""

    output_directory.mkdir(parents=True, exist_ok=True)
    if figure_3 and not approximate:
        topology_path = output_directory / "figure_3a_network_topology.png"
        scenario_path = output_directory / "figure_3b_scenario_i.png"
        combined_path = output_directory / "figure_3ab_scenario_i.png"
        metadata_path = output_directory / "figure_3ab_metadata.json"
    elif approximate:
        topology_path = output_directory / "approximate_figure_3a_topology.png"
        scenario_path = output_directory / "approximate_figure_3b_scenario_i.png"
        combined_path = output_directory / "approximate_figure_3ab_scenario_i.png"
        metadata_path = output_directory / "approximate_figure_3ab_metadata.json"
    else:
        topology_path = output_directory / "network_topology.png"
        scenario_path = output_directory / "scenario_i.png"
        combined_path = output_directory / "topology_and_scenario_i.png"
        metadata_path = output_directory / "scenario_metadata.json"
    png_metadata = {
        "Title": (
            "Tantur 2025 Fig. 3(a)-(b) methodological reproduction"
            if figure_3 and not approximate
            else "Approximation inspired by Tantur 2025 Fig. 3(a)-(b)"
            if approximate
            else "UWSN topology and Scenario-I plots"
        ),
        "Description": (
            _REPRODUCTION_NOTE
            if figure_3 or approximate
            else "Generated topology and Scenario-I solution plots."
        ),
    }

    figure_a, _ = plot_network_topology(env)
    figure_a.savefig(topology_path, dpi=200, metadata=png_metadata)
    plt.close(figure_a)

    figure_b, _ = plot_scenario_i(env, solution)
    figure_b.savefig(scenario_path, dpi=200, metadata=png_metadata)
    plt.close(figure_b)

    combined, axes = plt.subplots(
        1,
        2,
        figsize=(14.0, 6.0),
        constrained_layout=True,
    )
    plot_network_topology(env, ax=axes[0])
    plot_scenario_i(env, solution, ax=axes[1])
    if approximate:
        combined_title = "Section IV-B Scenario-I — explicit N_l=2 approximation"
    elif figure_3:
        combined_title = "Section IV-B Scenario-I — reproduction"
    else:
        combined_title = "UWSN topology and Scenario-I output"
    combined.suptitle(combined_title)
    combined.savefig(combined_path, dpi=200, metadata=png_metadata)
    plt.close(combined)

    artifact_paths = {
        "figure_3a": topology_path,
        "figure_3b": scenario_path,
        "figure_3ab": combined_path,
    }
    metadata_path.write_text(
        json.dumps(
            _metadata(
                env,
                solution,
                run_metadata=run_metadata,
                artifact_paths=artifact_paths,
                paper_reference=(
                    "Section IV-B, Fig. 3(a)-(b), Table III Scenario-I"
                    if figure_3 and not approximate
                    else "Approximation inspired by Section IV-B Fig. 3(a)-(b)"
                    if approximate
                    else None
                ),
                artifact_kind=(
                    "paper-model-methodological-reproduction"
                    if figure_3 and not approximate
                    else "explicit-n_l-2-approximation"
                    if approximate
                    else "generic-scenario-output"
                ),
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        **artifact_paths,
        "metadata": metadata_path,
    }


def save_scenario_outputs(
    env: EnvironmentData,
    solution: Solution,
    output_directory: Path,
    *,
    run_metadata: Mapping[str, object] | None = None,
) -> Mapping[str, Path]:
    """Save generic topology/scenario images without a Fig. 3 claim."""

    return _save_outputs(
        env,
        solution,
        output_directory,
        run_metadata=run_metadata,
        figure_3=False,
    )


def _validate_figure_3_environment(env: EnvironmentData) -> None:
    """Guard the paper-specific filename/metadata contract."""

    if len(env.network.sensors) != 12:
        raise ValueError("Fig. 3 requires exactly 12 sensor nodes")
    if env.experiment.volume_km != (1.0, 1.0, 0.30):
        raise ValueError("Fig. 3 requires the Section IV-B 1x1x0.30 km volume")
    if env.experiment.connectivity_counts != (12, 0, 0):
        raise ValueError("Fig. 3(b) requires Table III Scenario-I")
    if not np.allclose(env.network.deployment.positions_m[:, 2], 0.0):
        raise ValueError("Fig. 3 requires a two-dimensional deployment")


def save_figure_3_outputs(
    env: EnvironmentData,
    solution: Solution,
    output_directory: Path,
    *,
    run_metadata: Mapping[str, object] | None = None,
) -> Mapping[str, Path]:
    """Save validated Section IV-B Fig. 3(a)/(b) reproduction artifacts."""

    _validate_figure_3_environment(env)
    if env.paper.network.maximum_paths != 5:
        raise ValueError("paper-model Fig. 3 output requires Table I N_l=5")
    return _save_outputs(
        env,
        solution,
        output_directory,
        run_metadata=run_metadata,
        figure_3=True,
    )


def save_approximate_figure_3_outputs(
    env: EnvironmentData,
    solution: Solution,
    output_directory: Path,
    *,
    run_metadata: Mapping[str, object] | None = None,
) -> Mapping[str, Path]:
    """Save explicitly labeled tractable N_l=2 Scenario-I approximation."""

    _validate_figure_3_environment(env)
    if env.paper.network.maximum_paths != 2:
        raise ValueError("approximate Figure-3 output requires N_l=2")
    return _save_outputs(
        env,
        solution,
        output_directory,
        run_metadata=run_metadata,
        figure_3=False,
        approximate=True,
    )

"""Network environment for the Tantur et al. (2025) UWSN model.

This stage implements only deployment geometry and graph construction from
Section III-A. Acoustic energy and interference coefficients are added in
later stages.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .params import ExperimentParameters, PowerLevelTable

FloatArray  = NDArray[np.float64]
DirectedArc = tuple[int, int]


def _immutable_float_array(values: object) -> FloatArray :
    """Return an owned, read-only float64 array."""

    array = np.array(values, dtype=np.float64, copy=True)
    array.flags.writeable = False
    return array


@dataclass(frozen=True, slots=True)
class Deployment:
    """Positions of one base station and stationary underwater sensors.

    Paper: Section III-A and Fig. 1.

    ``positions_m[i]`` contains ``(x, y, z)`` in meters. Code uses node 0 for
    the BS, whereas the optimization equations in the paper use node 1.
    """

    positions_m : FloatArray
    bs_index    : int = 0

    def __post_init__(self) -> None :
        positions = _immutable_float_array(self.positions_m)

        if positions.ndim != 2 or positions.shape[1] != 3:
            raise ValueError("positions_m must have shape (number_of_nodes, 3)")

        if positions.shape[0] < 2:
            raise ValueError("a deployment requires one BS and at least one sensor")

        if not np.isfinite(positions).all():
            raise ValueError("positions_m must contain only finite coordinates")

        if self.bs_index != 0:
            raise ValueError("the implementation convention requires bs_index=0")
        object.__setattr__(self, "positions_m", positions)

    @property
    def number_of_nodes(self) -> int:
        """Return ``|V|``, including the BS."""

        return int(self.positions_m.shape[0])

    @property
    def number_of_sensors(self) -> int:
        """Return ``|W|``, excluding the BS."""

        return self.number_of_nodes - 1

    @property
    def nodes(self) -> tuple[int, ...]:
        """Return the paper's node set ``V`` using zero-based indices."""

        return tuple(range(self.number_of_nodes))

    @property
    def sensors(self) -> tuple[int, ...]:
        """Return the paper's sensor set ``W``."""

        return tuple(node for node in self.nodes if node != self.bs_index)


@dataclass(frozen=True, slots=True)
class NetworkEnvironment:
    """Geometry and directed graph primitives from Section III-A."""

    deployment                      : Deployment
    distances_m                     : FloatArray
    arcs                            : tuple[DirectedArc, ...]
    maximum_transmission_range_m    : float

    def __post_init__(self) -> None :
        distances       = _immutable_float_array(self.distances_m)
        expected_shape  = (
            self.deployment.number_of_nodes,
            self.deployment.number_of_nodes,
        )
        
        if distances.shape != expected_shape :
            raise ValueError(f"distances_m must have shape {expected_shape}")

        if self.maximum_transmission_range_m <= 0 :
            raise ValueError("maximum_transmission_range_m must be positive")

        valid_nodes = set(self.deployment.nodes)
        if len(set(self.arcs)) != len(self.arcs) :
            raise ValueError("arcs cannot contain duplicates")

        for source, target in self.arcs:
            if source not in valid_nodes or target not in valid_nodes :
                raise ValueError("arc endpoints must belong to V")

            if source == target :
                raise ValueError("self-loops are not part of A")

            if distances[source, target] > self.maximum_transmission_range_m :
                raise ValueError("arc distance exceeds the maximum range")

        object.__setattr__(self, "distances_m", distances)

    @property
    def nodes(self) -> tuple[int, ...] :
        """Return ``V``."""

        return self.deployment.nodes

    @property
    def sensors(self) -> tuple[int, ...] :
        """Return ``W``."""

        return self.deployment.sensors

    @property
    def bs_index(self) -> int :
        """Return the zero-based BS index."""

        return self.deployment.bs_index


def generate_uniform_deployment(
    experiment: ExperimentParameters,
    *,
    two_dimensional: bool = False,
) -> Deployment :
    """Generate the stationary uniform deployment described in Section III-A.

    Paper-defined behavior:
    - Sensors are uniformly distributed in a rectangular prism.
    - One static BS/sonobuoy is placed at a top corner.

    Implementation coordinate convention:
    - ``x`` spans ``[-d_x/2, d_x/2]``.
    - ``y`` spans ``[0, d_y]``.
    - Depth ``z`` spans ``[-d_z, 0]``.
    - The BS is at ``(-d_x/2, 0, 0)``.

    This convention preserves all distances and gives the Section IV-B
    two-dimensional case the paper's BS coordinate ``(-0.5, 0)`` when
    ``d_x=1 km``. Set ``two_dimensional=True`` to place all sensors at z=0.
    """

    dx_m, dy_m, dz_m    = (dimension * 1000.0 for dimension in experiment.volume_km)
    rng                 = np.random.default_rng(experiment.random_seed)

    positions           = np.empty((experiment.number_of_sensors + 1, 3), dtype=np.float64)
    positions[0]        = (-dx_m / 2.0, 0.0, 0.0)
    positions[1:, 0]    = rng.uniform(
        -dx_m / 2.0,
        dx_m / 2.0,
        experiment.number_of_sensors,
    )
    positions[1:, 1] = rng.uniform(0.0, dy_m, experiment.number_of_sensors)
    if two_dimensional:
        positions[1:, 2] = 0.0
    else:
        positions[1:, 2] = rng.uniform(-dz_m, 0.0, experiment.number_of_sensors)

    return Deployment(positions_m=positions)


def pairwise_distances(positions_m: FloatArray) -> FloatArray :
    """Calculate Euclidean ``d_ij`` for every pair of nodes.

    Paper: Section III-A and Table I.
    """

    positions = np.asarray(positions_m, dtype=np.float64)

    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError("positions_m must have shape (number_of_nodes, 3)")

    differences = positions[:, np.newaxis, :] - positions[np.newaxis, :, :]
    return np.linalg.norm(differences, axis=2)


def build_directed_arcs(
    distances_m: FloatArray,
    maximum_transmission_range_m: float,
) -> tuple[DirectedArc, ...] :
    """Build ``A={(i,j): i!=j, d_ij<=R_max(l_max)}``.

    Paper: Section III-A, network graph definition immediately after Fig. 1.
    The range comparison is inclusive, exactly as stated in the paper.
    """

    distances = np.asarray(distances_m, dtype=np.float64)
    if distances.ndim != 2 or distances.shape[0] != distances.shape[1]:
        raise ValueError("distances_m must be a square matrix")

    if not np.isfinite(distances).all() or np.any(distances < 0):
        raise ValueError("distances_m must contain finite non-negative values")

    if maximum_transmission_range_m <= 0:
        raise ValueError("maximum_transmission_range_m must be positive")

    number_of_nodes = distances.shape[0]
    return tuple(
        (source, target)
        for source in range(number_of_nodes)
        for target in range(number_of_nodes)
        if source != target
        and distances[source, target] <= maximum_transmission_range_m
    )


def build_network_environment(
    deployment: Deployment,
    maximum_transmission_range_m: float,
) -> NetworkEnvironment :
    """Build the Section III-A graph primitives for a deployment."""

    distances   = pairwise_distances(deployment.positions_m)
    arcs        = build_directed_arcs(distances, maximum_transmission_range_m)

    return NetworkEnvironment(
        deployment=deployment,
        distances_m=distances,
        arcs=arcs,
        maximum_transmission_range_m=maximum_transmission_range_m,
    )


def build_paper_network_environment(
    experiment: ExperimentParameters,
    *,
    power_levels: PowerLevelTable | None = None,
    two_dimensional: bool = False,
) -> NetworkEnvironment :
    """Generate a deployment and graph using ``R_max(l_max)`` from Table II."""

    table       = power_levels or PowerLevelTable()
    deployment  = generate_uniform_deployment(
        experiment,
        two_dimensional=two_dimensional,
    )
    
    return build_network_environment(deployment, table.ranges_m[-1])

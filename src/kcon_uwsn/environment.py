"""Network environment for the Tantur et al. (2025) UWSN model.

This stage implements only deployment geometry and graph construction from
Section III-A. Acoustic energy and interference coefficients are added in
later stages.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray

from .params import AcousticParameters, ExperimentParameters, PowerLevelTable

FloatArray  = NDArray[np.float64]
DirectedArc = tuple[int, int]


def _immutable_float_array(values : object) -> FloatArray :
    """Return an owned, read-only float64 array."""

    array = np.array(values, dtype=np.float64, copy=True)
    array.flags.writeable = False
    return array


@dataclass(frozen=True, slots=True)
class Deployment :
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
class NetworkEnvironment :
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
    experiment      : ExperimentParameters, 
    *,
    two_dimensional : bool = False,
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

    positions = np.empty(
        (experiment.number_of_sensors + 1, 3),
        dtype=np.float64,
    )
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
    distances_m                     : FloatArray,
    maximum_transmission_range_m    : float,
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
    deployment                      : Deployment,
    maximum_transmission_range_m    : float,
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
    experiment          : ExperimentParameters,
    *,
    power_levels        : PowerLevelTable | None = None,
    two_dimensional     : bool = False,
) -> NetworkEnvironment :
    """Generate a deployment and graph using ``R_max(l_max)`` from Table II."""

    table       = power_levels or PowerLevelTable()
    deployment  = generate_uniform_deployment(
        experiment,
        two_dimensional=two_dimensional,
    )
    
    return build_network_environment(deployment, table.ranges_m[-1])


def absorption_coefficient_db_per_km(operating_frequency_khz: float) -> float :
    """Calculate the absorption coefficient ``alpha(f_0)``.

    Paper: Section III-B, Eq. (2). Frequency is expressed in kHz and the
    returned coefficient is in dB/km.
    """

    if operating_frequency_khz <= 0 :
        raise ValueError("operating_frequency_khz must be positive")

    frequency_squared = operating_frequency_khz**2
    return (
        0.11 * frequency_squared / (1.0 + frequency_squared)
        + 44.0 * frequency_squared / (4100.0 + frequency_squared)
        + 2.75e-4 * frequency_squared
        + 0.003
    )


def frequency_component(absorption_db_per_km: float) -> float :
    """Calculate ``nu=10^(alpha(f_0)/10)`` used by Eq. (1).

    Paper: Section III-B, definition immediately following Eq. (1).
    """

    if absorption_db_per_km < 0 :
        raise ValueError("absorption_db_per_km cannot be negative")
    return 10.0 ** (absorption_db_per_km / 10.0)


def transmission_loss(
    distance_m                      : float,
    spreading_factor                : float,
    frequency_dependent_component   : float,
) -> float :
    """Calculate acoustic ``TL(R_max(l))`` for a distance in meters.

    Paper: Section III-B, Eq. (1). The ``10^-3`` factor converts the supplied
    meter distance to kilometers in the absorption term.
    """

    if distance_m <= 0 :
        raise ValueError("distance_m must be positive")

    if spreading_factor <= 0 :
        raise ValueError("spreading_factor must be positive")
        
    if frequency_dependent_component <= 0 :
        raise ValueError("frequency_dependent_component must be positive")

    return distance_m**spreading_factor * frequency_dependent_component ** (
        1e-3 * distance_m
    )


def transmission_energy_j_per_bit(
    loss                                : float,
    desired_receiver_input_j_per_bit    : float,
) -> float :
    """Calculate ``E_T(l)`` in J/bit.

    Paper: Section III-B, Eq. (3).
    """

    if loss <= 0 :
        raise ValueError("loss must be positive")

    if desired_receiver_input_j_per_bit <= 0 :
        raise ValueError("desired_receiver_input_j_per_bit must be positive")

    return loss * desired_receiver_input_j_per_bit


def power_level_energies_j_per_bit(
    acoustic        : AcousticParameters,
    power_levels    : PowerLevelTable,
) -> tuple[float, ...] :
    """Calculate ``E_T(l)`` for all ten Table II power levels.

    Paper: Section III-B, Eqs. (1)–(3), and Table II.
    """

    alpha       = absorption_coefficient_db_per_km(acoustic.operating_frequency_khz)
    component   = frequency_component(alpha)
    return tuple(
        transmission_energy_j_per_bit(
            transmission_loss(
                distance_m                      = distance_m,
                spreading_factor                = acoustic.spreading_factor,
                frequency_dependent_component   = component,
            ),
            acoustic.desired_receiver_input_j_per_bit,
        )
        for distance_m in power_levels.ranges_m
    )


def minimum_link_transmission_energy_j_per_bit(
    distance_m                  : float,
    power_levels                : PowerLevelTable,
    level_energies_j_per_bit    : tuple[float, ...],
) -> float :
    """Select the minimum power level covering ``d_ij``.

    Paper: Section III-B, Eq. (5). A distance equal to a range boundary uses
    that level. Distances beyond ``R_max(10)`` have infinite energy.
    """

    if distance_m < 0 :
        raise ValueError("distance_m cannot be negative")

    if len(level_energies_j_per_bit) != len(power_levels.levels) :
        raise ValueError("one energy value is required for each power level")
        
    if any(energy <= 0 for energy in level_energies_j_per_bit) :
        raise ValueError("power-level energies must be positive")

    for maximum_range_m, energy in zip(
        power_levels.ranges_m,
        level_energies_j_per_bit,
        strict=True,
    ):
        if distance_m <= maximum_range_m:
            return energy
    return float("inf")


@dataclass(frozen=True, slots=True)
class AcousticEnergyEnvironment :
    """Acoustic coefficients and per-arc energies from Section III-B."""

    network                                 : NetworkEnvironment
    absorption_db_per_km                    : float
    frequency_dependent_component           : float
    transmission_loss_by_level              : tuple[float, ...]
    transmission_energy_by_level_j_per_bit  : tuple[float, ...]
    reception_energy_j_per_bit              : float
    link_transmission_energy_j_per_bit      : Mapping[DirectedArc, float]

    def __post_init__(self) -> None :
        number_of_levels = len(self.transmission_loss_by_level)
        
        if number_of_levels != 10 :
            raise ValueError("the paper's energy model requires 10 power levels")

        if len(self.transmission_energy_by_level_j_per_bit) != number_of_levels :
            raise ValueError("loss and energy tuples must have equal lengths")

        if self.absorption_db_per_km < 0 :
            raise ValueError("absorption_db_per_km cannot be negative")

        if self.frequency_dependent_component <= 0 :
            raise ValueError("frequency_dependent_component must be positive")

        if self.reception_energy_j_per_bit <= 0 :
            raise ValueError("reception_energy_j_per_bit must be positive")

        link_energies = dict(self.link_transmission_energy_j_per_bit)
        if set(link_energies) != set(self.network.arcs):
            raise ValueError("link energy keys must equal the directed arc set A")
        
        invalid_energy = any(
            not np.isfinite(value) or value <= 0 for value in link_energies.values()
        )
        if invalid_energy :
            raise ValueError("every arc must have a finite positive energy")

        object.__setattr__(
            self,
            "link_transmission_energy_j_per_bit",
            MappingProxyType(link_energies),
        )


def build_acoustic_energy_environment(
    network         : NetworkEnvironment,
    *,
    acoustic        : AcousticParameters | None = None,
    power_levels    : PowerLevelTable | None = None,
) -> AcousticEnergyEnvironment:
    """Build all Section III-B coefficients needed by the later MILP."""

    acoustic_parameters = acoustic or AcousticParameters()
    table               = power_levels or PowerLevelTable()
    alpha               = absorption_coefficient_db_per_km(
                            acoustic_parameters.operating_frequency_khz
                        )
    component           = frequency_component(alpha)
    losses              = tuple(
                            transmission_loss(
                                distance_m                      = distance_m,
                                spreading_factor                = acoustic_parameters.spreading_factor,
                                frequency_dependent_component   = component,
                            )
                            for distance_m in table.ranges_m
                        )
    level_energies      = tuple(
                            transmission_energy_j_per_bit(
                                loss,
                                acoustic_parameters.desired_receiver_input_j_per_bit,
                            )
                            for loss in losses
                        )
    link_energies       = {
                            arc: minimum_link_transmission_energy_j_per_bit(
                                network.distances_m[arc],
                                table,
                                level_energies,
                            )
                            for arc in network.arcs
                        }

    return AcousticEnergyEnvironment(
        network                                 = network,
        absorption_db_per_km                    = alpha,
        frequency_dependent_component           = component,
        transmission_loss_by_level              = losses,
        transmission_energy_by_level_j_per_bit  = level_energies,
        # Paper: Section III-B, Eq. (4), E_R=P_r.
        reception_energy_j_per_bit              = acoustic_parameters.reception_energy_j_per_bit,
        link_transmission_energy_j_per_bit      = link_energies,
    )

"""
Network environment for the Tantur et al. (2025) UWSN model.

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

from .params import (
    AcousticParameters,
    ExperimentParameters,
    PaperParameters,
    PowerLevelTable,
)

"""N-dimensional array"""
FloatArray  = NDArray[np.float64]

"""Tuple array with two integer values to describe directed arcs."""
DirectedArc = tuple[int, int]


"""Return an owned, read-only float64 array."""
def _immutable_float_array(values: object) -> FloatArray :
    array                 = np.array(values, dtype=np.float64, copy=True)
    array.flags.writeable = False
    return array


"""
    Positions of one base station and stationary underwater sensors.

    Paper: Section III-A and Fig. 1.

    ``positions_m[i]`` contains ``(x, y, z)`` in meters. 
    
    !!IMPORTANT!!
    Code uses node 0 for the BS, whereas the optimization equations in the paper use node 1.
"""
@dataclass(frozen=True, slots=True)
class Deployment :
    positions_m : FloatArray
    bs_index    : int = 0

    def __post_init__(self) -> None :
        positions = _immutable_float_array(self.positions_m)

        ## Number of dimesion and dimesion check
        if positions.ndim != 2 or positions.shape[1] != 3 :
            raise ValueError("positions_m must have shape (number_of_nodes, 3)")

        ## At least one BS and one sensor should exist
        if positions.shape[0] < 2 :
            raise ValueError("a deployment requires one BS and at least one sensor")

        ## Placement coordinate check
        if not np.isfinite(positions).all() :
            raise ValueError("positions_m must contain only finite coordinates")

        ## BS should be replaced to 0
        if self.bs_index != 0 :
            raise ValueError("the implementation convention requires bs_index=0")
        object.__setattr__(self, "positions_m", positions)

    """Return ``|V|``, including the BS."""
    @property
    def number_of_nodes(self) -> int :
        return int(self.positions_m.shape[0])

    """Return ``|W|``, excluding the BS."""
    @property
    def number_of_sensors(self) -> int :
        return self.number_of_nodes - 1

    """Return the paper's node set ``V`` using zero-based indices."""
    @property
    def nodes(self) -> tuple[int, ...] :
        return tuple(range(self.number_of_nodes))

    """Return the paper's sensor set ``W``."""
    @property
    def sensors(self) -> tuple[int, ...] :
        return tuple(node for node in self.nodes if node != self.bs_index)


"""Geometry and directed graph primitives from Section III-A."""
@dataclass(frozen=True, slots=True)
class NetworkEnvironment :

    deployment                   : Deployment
    distances_m                  : FloatArray
    arcs                         : tuple[DirectedArc, ...]
    maximum_transmission_range_m : float

    def __post_init__(self) -> None :
        distances      = _immutable_float_array(self.distances_m)
        expected_shape = (
            self.deployment.number_of_nodes,
            self.deployment.number_of_nodes,
        )

        if distances.shape != expected_shape :
            raise ValueError(f"distances_m must have shape {expected_shape}")

        ## Transmission range check
        if self.maximum_transmission_range_m <= 0 :
            raise ValueError("maximum_transmission_range_m must be positive")

        ## Check number of arcs
        valid_nodes = set(self.deployment.nodes)
        if len(set(self.arcs)) != len(self.arcs) :
            raise ValueError("arcs cannot contain duplicates")

        ## Arcs between nodes are checked
        for source, target in self.arcs :
            if source not in valid_nodes or target not in valid_nodes :
                raise ValueError("arc endpoints must belong to V")

            if source == target :
                raise ValueError("self-loops are not part of A")

            if distances[source, target] > self.maximum_transmission_range_m :
                raise ValueError("arc distance exceeds the maximum range")

        object.__setattr__(self, "distances_m", distances)


    """Return ``V``."""
    @property
    def nodes(self) -> tuple[int, ...] :
        return self.deployment.nodes

    """Return ``W``."""
    @property
    def sensors(self) -> tuple[int, ...] :
        return self.deployment.sensors

    """Return the zero-based BS index."""
    @property
    def bs_index(self) -> int :
        return self.deployment.bs_index


"""
    Generate the stationary uniform deployment described in Section III-A.

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
def generate_uniform_deployment(
    experiment      : ExperimentParameters,
    *,
    two_dimensional : bool = False,
) -> Deployment :
    ## Positions converted to the km
    dx_m, dy_m, dz_m = (dimension * 1000.0 for dimension in experiment.volume_km)
    rng              = np.random.default_rng(experiment.random_seed)

    ## Empty postions list
    positions = np.empty(
        (experiment.number_of_sensors + 1, 3),
        dtype=np.float64,
    )

    ## Place BS to a corner
    positions[0] = (-dx_m / 2.0, 0.0, 0.0)

    ## Place all sensors as uniformly distributed in x-axis
    positions[1:, 0] = rng.uniform(
        -dx_m / 2.0,
        dx_m / 2.0,
        experiment.number_of_sensors,
    )

    ## Place all sensors as uniformly distributed in y-axis
    positions[1:, 1] = rng.uniform(0.0, dy_m, experiment.number_of_sensors)

    ## Place all sensors as uniformly distributed in z-axis
    if two_dimensional:
        positions[1:, 2] = 0.0
    else:
        positions[1:, 2] = rng.uniform(-dz_m, 0.0, experiment.number_of_sensors)

    return Deployment(positions_m=positions)


"""
    Calculate Euclidean ``d_ij`` for every pair of nodes.

    Paper: Section III-A and Table I.
"""
def pairwise_distances(positions_m: FloatArray) -> FloatArray :
    positions = np.asarray(positions_m, dtype=np.float64)

    if positions.ndim != 2 or positions.shape[1] != 3 :
        raise ValueError("positions_m must have shape (number_of_nodes, 3)")

    differences = positions[:, np.newaxis, :] - positions[np.newaxis, :, :]
    return np.linalg.norm(differences, axis=2)


"""
    Build ``A={(i,j): i!=j, d_ij<=R_max(l_max)}``.

    Paper: Section III-A, network graph definition immediately after Fig. 1.
    The range comparison is inclusive, exactly as stated in the paper.
"""
def build_directed_arcs(
    distances_m                  : FloatArray,
    maximum_transmission_range_m : float,
) -> tuple[DirectedArc, ...] :
    distances = np.asarray(distances_m, dtype=np.float64)
    if distances.ndim != 2 or distances.shape[0] != distances.shape[1] :
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


"""Build the Section III-A graph primitives for a deployment."""
def build_network_environment(
    deployment                   : Deployment,
    maximum_transmission_range_m : float,
) -> NetworkEnvironment :
    distances = pairwise_distances(deployment.positions_m)
    arcs      = build_directed_arcs(distances, maximum_transmission_range_m)

    return NetworkEnvironment(
        deployment                   = deployment,
        distances_m                  = distances,
        arcs                         = arcs,
        maximum_transmission_range_m = maximum_transmission_range_m,
    )


"""Generate a deployment and graph using ``R_max(l_max)`` from Table II."""
def build_paper_network_environment(
    experiment      : ExperimentParameters,
    *,
    power_levels    : PowerLevelTable | None = None,
    two_dimensional : bool = False,
) -> NetworkEnvironment :

    table      = power_levels or PowerLevelTable()
    deployment = generate_uniform_deployment(
        experiment,
        two_dimensional=two_dimensional,
    )

    return build_network_environment(deployment, table.ranges_m[-1])

"""
    Calculate the absorption coefficient ``alpha(f_0)``.

    Paper: Section III-B, Eq. (2). Frequency is expressed in kHz and the
    returned coefficient is in dB/km.
"""
def absorption_coefficient_db_per_km(operating_frequency_khz: float) -> float :
    if operating_frequency_khz <= 0 :
        raise ValueError("operating_frequency_khz must be positive")

    frequency_squared = operating_frequency_khz**2
    return (
        0.11 * frequency_squared / (1.0 + frequency_squared)
        + 44.0 * frequency_squared / (4100.0 + frequency_squared)
        + 2.75e-4 * frequency_squared
        + 0.003
    )


"""
    Calculate ``nu=10^(alpha(f_0)/10)`` used by Eq. (1).

    Paper: Section III-B, definition immediately following Eq. (1).
"""
def frequency_component(absorption_db_per_km: float) -> float :
    if absorption_db_per_km < 0 :
        raise ValueError("absorption_db_per_km cannot be negative")
    return 10.0 ** (absorption_db_per_km / 10.0)


"""
    Calculate acoustic ``TL(R_max(l))`` for a distance in meters.

    Paper: Section III-B, Eq. (1). The ``10^-3`` factor converts the supplied
    meter distance to kilometers in the absorption term.
"""
def transmission_loss(
    distance_m                      : float,
    spreading_factor                : float,
    frequency_dependent_component   : float,
) -> float :
    if distance_m <= 0 :
        raise ValueError("distance_m must be positive")

    if spreading_factor <= 0 :
        raise ValueError("spreading_factor must be positive")

    if frequency_dependent_component <= 0 :
        raise ValueError("frequency_dependent_component must be positive")

    return distance_m**spreading_factor * frequency_dependent_component ** (
        1e-3 * distance_m
    )


"""
    Calculate ``E_T(l)`` in J/bit.

    Paper: Section III-B, Eq. (3).
"""
def transmission_energy_j_per_bit(
    loss                             : float,
    desired_receiver_input_j_per_bit : float,
) -> float :
    if loss <= 0 :
        raise ValueError("loss must be positive")

    if desired_receiver_input_j_per_bit <= 0 :
        raise ValueError("desired_receiver_input_j_per_bit must be positive")

    return loss * desired_receiver_input_j_per_bit


"""
    Calculate ``E_T(l)`` for all ten Table II power levels.

    Paper: Section III-B, Eqs. (1)–(3), and Table II.
"""
def power_level_energies_j_per_bit(
    acoustic        : AcousticParameters,
    power_levels    : PowerLevelTable,
) -> tuple[float, ...] :

    alpha     = absorption_coefficient_db_per_km(acoustic.operating_frequency_khz)
    component = frequency_component(alpha)

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


"""
    Select the minimum power level covering ``d_ij``.

    Paper: Section III-B, Eq. (5). A distance equal to a range boundary uses
    that level. Distances beyond ``R_max(10)`` have infinite energy.
"""
def minimum_link_transmission_energy_j_per_bit(
    distance_m               : float,
    power_levels             : PowerLevelTable,
    level_energies_j_per_bit : tuple[float, ...],
) -> float :
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
    ) :
        if distance_m <= maximum_range_m :
            return energy
    return float("inf")


"""Acoustic coefficients and per-arc energies from Section III-B."""
@dataclass(frozen=True, slots=True)
class AcousticEnergyEnvironment :
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
        if set(link_energies) != set(self.network.arcs) :
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


"""Build all Section III-B coefficients needed by the later MILP."""
def build_acoustic_energy_environment(
    network      : NetworkEnvironment,
    *,
    acoustic     : AcousticParameters | None = None,
    power_levels : PowerLevelTable | None = None,
) -> AcousticEnergyEnvironment :

    acoustic_parameters = acoustic or AcousticParameters()
    table               = power_levels or PowerLevelTable()
    alpha               = absorption_coefficient_db_per_km(
        acoustic_parameters.operating_frequency_khz
    )
    component = frequency_component(alpha)
    losses    = tuple(
        transmission_loss(
            distance_m                      = distance_m,
            spreading_factor                = (acoustic_parameters.spreading_factor),
            frequency_dependent_component   = component,
        )
        for distance_m in table.ranges_m
    )
    level_energies = tuple(
        transmission_energy_j_per_bit(
            loss,
            acoustic_parameters.desired_receiver_input_j_per_bit,
        )
        for loss in losses
    )
    link_energies = {
        arc : minimum_link_transmission_energy_j_per_bit(
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
        reception_energy_j_per_bit              = float(
            acoustic_parameters.reception_energy_j_per_bit
        ),
        link_transmission_energy_j_per_bit      = link_energies,
    )


"""
    Disjoint sensor subsets ``W_n`` and their required ``kappa_n``.

    Paper: Section III-A, Constraint (18), and Tables III-IV.
"""
@dataclass(frozen=True, slots=True)
class ConnectivityPartition :
    sensors         : tuple[int, ...]
    sets_by_kappa   : Mapping[int, tuple[int, ...]]
    kappa_by_sensor : Mapping[int, int]

    def __post_init__(self) -> None :
        sensors = tuple(self.sensors)
        if len(set(sensors)) != len(sensors) :
            raise ValueError("sensor indices must be unique")

        normalized_sets = {
            int(kappa) : tuple(nodes) for kappa, nodes in self.sets_by_kappa.items()
        }
        assigned_nodes = [node for nodes in normalized_sets.values() for node in nodes]
        if len(set(assigned_nodes)) != len(assigned_nodes) :
            raise ValueError("W_n subsets must be pairwise disjoint")

        if set(assigned_nodes) != set(sensors) :
            raise ValueError("W_n subsets must partition all sensors")

        expected_mapping = {
            node : kappa for kappa, nodes in normalized_sets.items() for node in nodes
        }
        supplied_mapping = dict(self.kappa_by_sensor)
        if supplied_mapping != expected_mapping :
            raise ValueError("kappa_by_sensor must agree with the W_n subsets")

        object.__setattr__(self, "sensors", sensors)
        object.__setattr__(
            self,
            "sets_by_kappa",
            MappingProxyType(normalized_sets),
        )
        object.__setattr__(
            self,
            "kappa_by_sensor",
            MappingProxyType(supplied_mapping),
        )

"""
    Build explicitly supplied ``W_n`` sets.

    Paper: Section III-A, Constraint (18), and Table III scenarios.
"""
def build_explicit_connectivity_partition(
    sensors             : tuple[int, ...],
    sets_by_kappa       : Mapping[int, tuple[int, ...]],
    *,
    connectivity_range  : tuple[int, int] = (1, 3),
    maximum_paths       : int = 5,
) -> ConnectivityPartition :
    kappa_min, kappa_max = connectivity_range
    normalized_sets : dict[int, tuple[int, ...]] = {}
    for kappa, nodes in sets_by_kappa.items() :
        if not kappa_min <= kappa <= kappa_max :
            raise ValueError("kappa is outside the paper's connectivity range")

        if kappa > maximum_paths :
            raise ValueError("kappa cannot exceed N_l")

        normalized_sets[int(kappa)] = tuple(nodes)

    mapping = {
        node : kappa for kappa, nodes in normalized_sets.items() for node in nodes
    }
    return ConnectivityPartition(
        sensors         = sensors,
        sets_by_kappa   = normalized_sets,
        kappa_by_sensor = mapping,
    )


"""
    Randomly assign sensors to ``W_1``, ``W_2``, and ``W_3``.

    Paper: Section IV-C states that sensors are assigned randomly to ``W_n``.
    A fixed seed is an implementation addition for reproducibility.
"""
def build_seeded_connectivity_partition(
    sensors             : tuple[int, ...],
    connectivity_counts : tuple[int, int, int],
    *,
    random_seed         : int,
    maximum_paths       : int = 5,
) -> ConnectivityPartition :
    if len(connectivity_counts) != 3 :
        raise ValueError("connectivity_counts must contain |W_1|, |W_2|, |W_3|")

    if any(count < 0 for count in connectivity_counts) :
        raise ValueError("connectivity counts cannot be negative")

    if sum(connectivity_counts) != len(sensors) :
        raise ValueError("connectivity counts must cover all sensors")

    generator        = np.random.default_rng(random_seed)
    shuffled_sensors = tuple(
        int(node) for node in generator.permutation(np.asarray(sensors))
    )
    sets_by_kappa : dict[int, tuple[int, ...]] = {}
    start                                      = 0
    for kappa, count in enumerate(connectivity_counts, start=1):
        stop = start + count
        sets_by_kappa[kappa] = shuffled_sensors[start:stop]
        start = stop

    return build_explicit_connectivity_partition(
        sensors,
        sets_by_kappa,
        connectivity_range=(1, 3),
        maximum_paths=maximum_paths,
    )


"""Sparse Eq. (26) interference indicators for every node and arc."""
@dataclass(frozen=True, slots=True)
class InterferenceEnvironment :
    network                  : NetworkEnvironment
    range_multiplier         : float
    interfering_arcs_by_node : Mapping[int, tuple[DirectedArc, ...]]

    def __post_init__(self) -> None :
        if self.range_multiplier <= 0 :
            raise ValueError("range_multiplier must be positive")

        normalized = {
            int(node) : tuple(arcs)
            for node, arcs in self.interfering_arcs_by_node.items()
        }

        if set(normalized) != set(self.network.nodes) :
            raise ValueError("interference mapping must contain every node in V")

        valid_arcs = set(self.network.arcs)
        for arcs in normalized.values() :
            if not set(arcs) <= valid_arcs:
                raise ValueError("interference mapping contains an arc outside A")
        object.__setattr__(
            self,
            "interfering_arcs_by_node",
            MappingProxyType(normalized),
        )

    """Return ``I^i_jm`` from Eq. (26) as zero or one."""
    def indicator(self, node: int, arc: DirectedArc) -> int :
        if node not in self.interfering_arcs_by_node :
            raise KeyError(f"node {node} is not in V")

        if arc not in self.network.arcs :
            raise KeyError(f"arc {arc} is not in A")

        return int(arc in self.interfering_arcs_by_node[node])

"""
    Calculate ``I^i_jm=1`` iff ``gamma*d_jm>=d_ji``.

    Paper: Section III-C, Eq. (26). Indicators are calculated for every
    ``i in V`` and every directed communication link ``(j,m) in A``. Only
    indicators equal to one are stored.
"""
def build_interference_environment(
    network          : NetworkEnvironment,
    range_multiplier : float,
) -> InterferenceEnvironment :
    interfering_arcs_by_node = {
        node : tuple(
            (transmitter, receiver)
            for transmitter, receiver in network.arcs
            if range_multiplier * network.distances_m[transmitter, receiver]
            >= network.distances_m[transmitter, node]
        )
        for node in network.nodes
    }
    return InterferenceEnvironment(
        network                  = network,
        range_multiplier         = range_multiplier,
        interfering_arcs_by_node = interfering_arcs_by_node,
    )

"""Complete solver-independent input for the paper MILP."""
@dataclass(frozen=True, slots=True)
class EnvironmentData:
    experiment   : ExperimentParameters
    paper        : PaperParameters
    energy       : AcousticEnergyEnvironment
    connectivity : ConnectivityPartition
    interference : InterferenceEnvironment

    def __post_init__(self) -> None :
        network = self.energy.network
        if self.interference.network is not network :
            raise ValueError("energy and interference must use the same network")

        if self.connectivity.sensors != network.sensors :
            raise ValueError("connectivity partition must cover network sensors")

        self.paper.validate_experiment(self.experiment)

    """Return the underlying Section III-A network."""
    @property
    def network(self) -> NetworkEnvironment:
        return self.energy.network

"""Build all paper coefficients implemented through Stage 4."""
def build_environment(
    experiment                  : ExperimentParameters,
    *,
    paper                       : PaperParameters | None = None,
    explicit_connectivity_sets  : Mapping[int, tuple[int, ...]] | None = None,
    two_dimensional             : bool = False,
) -> EnvironmentData :
    paper_parameters = paper or PaperParameters()
    paper_parameters.validate_experiment(experiment)
    
    network = build_paper_network_environment(
        experiment,
        power_levels    = paper_parameters.power_levels,
        two_dimensional = two_dimensional,
    )
    energy = build_acoustic_energy_environment(
        network,
        acoustic     = paper_parameters.acoustic,
        power_levels = paper_parameters.power_levels,
    )

    if explicit_connectivity_sets is None :
        # Section IV-C randomizes topology and W_n assignment independently.
        assignment_seed = int(
            np.random.SeedSequence(experiment.random_seed)
            .spawn(2)[1]
            .generate_state(1)[0]
        )
        connectivity = build_seeded_connectivity_partition(
            network.sensors,
            experiment.connectivity_counts,
            random_seed     = assignment_seed,
            maximum_paths   = paper_parameters.network.maximum_paths,
        )
    else:
        connectivity = build_explicit_connectivity_partition(
            network.sensors,
            explicit_connectivity_sets,
            connectivity_range  = paper_parameters.network.connectivity_range,
            maximum_paths       = paper_parameters.network.maximum_paths,
        )
        actual_counts = tuple(
            len(connectivity.sets_by_kappa.get(kappa, ())) for kappa in range(1, 4)
        )
        if actual_counts != experiment.connectivity_counts :
            raise ValueError(
                "explicit W_n cardinalities must match connectivity_counts"
            )

    interference = build_interference_environment(
        network,
        paper_parameters.network.interference_range_multiplier,
    )
    return EnvironmentData(
        experiment   = experiment,
        paper        = paper_parameters,
        energy       = energy,
        connectivity = connectivity,
        interference = interference,
    )

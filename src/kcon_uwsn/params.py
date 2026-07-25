"""
Parameters transcribed from Tantur et al. (2025).

Paper notation is retained in docstrings while Python names include units. The
paper reports transmission energies in mJ/bit; the optimization implementation
will use J/bit internally.
"""

from __future__ import annotations

from dataclasses import dataclass, field

"""
    Traffic, timing, and connectivity parameters.

    Paper: Section III-A and Table I.
"""
@dataclass(frozen=True, slots=True)
class NetworkParameters :
    # Paper: Section III-A and Table I (N_r, t_r, s_k, l_d, l_c).
    number_of_rounds             : int   = 1440
    round_duration_s             : float = 300.0
    packets_per_sensor_per_round : int   = 1
    data_packet_size_bits        : int   = 1024
    control_packet_size_bits     : int   = 256

    # Paper: Table I (R_b, N_l, M, gamma, xi, and kappa_n).
    data_rate_bps                   : float = 2500.0
    maximum_paths                   : int   = 5
    big_m                           : int  = 10_000
    interference_range_multiplier   : float = 1.7
    control_frequency_range         : tuple[float, float] = (0.25, 4.0)
    connectivity_range              : tuple[int, int] = (1, 3)

    def __post_init__(self) -> None :
        positive_values = {
            "number_of_rounds"              : self.number_of_rounds,
            "round_duration_s"              : self.round_duration_s,
            "packets_per_sensor_per_round"  : self.packets_per_sensor_per_round,
            "data_packet_size_bits"         : self.data_packet_size_bits,
            "control_packet_size_bits"      : self.control_packet_size_bits,
            "data_rate_bps"                 : self.data_rate_bps,
            "maximum_paths"                 : self.maximum_paths,
            "big_m"                         : self.big_m,
            "interference_range_multiplier" : self.interference_range_multiplier,
        }

        for name, value in positive_values.items() :
            if value <= 0 :
                raise ValueError(f"{name} must be positive, got {value}")

        xi_min, xi_max = self.control_frequency_range
        if not 0 < xi_min <= xi_max :
            raise ValueError("control_frequency_range must be positive and ordered")

        kappa_min, kappa_max = self.connectivity_range
        if not 1 <= kappa_min <= kappa_max :
            raise ValueError("connectivity_range must start at 1 and be ordered")
        if kappa_max > self.maximum_paths :
            raise ValueError("maximum connectivity cannot exceed maximum_paths")


"""
    Underwater acoustic energy-model parameters.

    Paper: Section III-B and Table I.
"""
@dataclass(frozen=True, slots=True)
class AcousticParameters :
    # Paper: Eqs. (1)-(4) and Table I (f_0, k_s, P_0, P_r).
    operating_frequency_khz          : float = 25.0
    spreading_factor                 : float = 1.5
    desired_receiver_input_j_per_bit : float = 1e-7
    reception_energy_j_per_bit       : float = 0.2e-7

    def __post_init__(self) -> None :
        for name, value in (
            ("operating_frequency_khz", self.operating_frequency_khz),
            ("spreading_factor", self.spreading_factor),
            ("desired_receiver_input_j_per_bit", self.desired_receiver_input_j_per_bit),
            ("reception_energy_j_per_bit", self.reception_energy_j_per_bit),
        ):
            if value <= 0 :
                raise ValueError(f"{name} must be positive, got {value}")


"""
    Published transmission ranges and reference energies.

    Paper: Section III-B, Eq. (5), and Table II.

    The Table II energy values are retained as reference data for validating the
    calculations implemented in Stage 3. They are converted from mJ/bit to
    J/bit by :attr:`transmission_energy_j_per_bit`.
"""
@dataclass(frozen=True, slots=True)
class PowerLevelTable :
    levels   : tuple[int, ...]   = tuple(range(1, 11))
    ranges_m : tuple[float, ...] = (
        100.0,
        200.0,
        300.0,
        400.0,
        500.0,
        600.0,
        700.0,
        800.0,
        900.0,
        1000.0,
    )
    transmission_energy_mj_per_bit : tuple[float, ...] = (
        0.115,
        0.375,
        0.792,
        1.404,
        2.258,
        3.416,
        4.954,
        6.967,
        9.568,
        12.897,
    )

    def __post_init__(self) -> None :
        size = len(self.levels)
        if size != 10 :
            raise ValueError(f"the paper defines 10 power levels, got {size}")

        if len(self.ranges_m) != size :
            raise ValueError("each power level must have one transmission range")

        if len(self.transmission_energy_mj_per_bit) != size :
            raise ValueError("each power level must have one transmission energy")

        if self.levels != tuple(range(1, 11)) :
            raise ValueError("power levels must be the consecutive values 1 through 10")

        if any(value <= 0 for value in self.ranges_m) :
            raise ValueError("transmission ranges must be positive")

        if any(value <= 0 for value in self.transmission_energy_mj_per_bit) :
            raise ValueError("transmission energies must be positive")

        adjacent_ranges = zip(self.ranges_m, self.ranges_m[1:], strict=False)
        if any(left >= right for left, right in adjacent_ranges) :
            raise ValueError("transmission ranges must be strictly increasing")

    """Return Table II energies converted from mJ/bit to J/bit."""
    @property
    def transmission_energy_j_per_bit(self) -> tuple[float, ...] :
        return tuple(value * 1e-3 for value in self.transmission_energy_mj_per_bit)


"""
    Parameters selecting one paper-style deployment and kappa assignment.

    Paper: Section III-A, Table I, and Tables III-IV.

    ``connectivity_counts`` stores ``(|W_1|, |W_2|, |W_3|)``. The explicit
    node membership of each set is an environment concern implemented in
    Stage 4.
"""
@dataclass(frozen=True, slots=True)
class ExperimentParameters :
    number_of_sensors           : int                        = 30
    volume_km                   : tuple[float, float, float] = (1.0, 3.0, 0.30)
    control_to_data_frequency   : float                      = 1.0
    connectivity_counts         : tuple[int, int, int]       = (30, 0, 0)
    random_seed                 : int                        = 42

    def __post_init__(self) -> None :
        if self.number_of_sensors <= 0 :
            raise ValueError("number_of_sensors must be positive")

        if len(self.volume_km) != 3 or any(length <= 0 for length in self.volume_km) :
            raise ValueError("volume_km must contain three positive dimensions")

        if self.control_to_data_frequency <= 0 :
            raise ValueError("control_to_data_frequency must be positive")

        if len(self.connectivity_counts) != 3 :
            raise ValueError("connectivity_counts must be (|W_1|, |W_2|, |W_3|)")

        if any(count < 0 for count in self.connectivity_counts) :
            raise ValueError("connectivity partition counts cannot be negative")

        if sum(self.connectivity_counts) != self.number_of_sensors :
            raise ValueError(
                "connectivity partition counts must sum to number_of_sensors"
            )

"""Complete immutable parameter bundle used by later stages."""
@dataclass(frozen=True, slots=True)
class PaperParameters :
    network      : NetworkParameters  = field(default_factory=NetworkParameters)
    acoustic     : AcousticParameters = field(default_factory=AcousticParameters)
    power_levels : PowerLevelTable    = field(default_factory=PowerLevelTable)

    """Validate an experiment against the ranges studied in the paper."""
    def validate_experiment(self, experiment: ExperimentParameters) -> None :
        xi_min, xi_max = self.network.control_frequency_range
        if not xi_min <= experiment.control_to_data_frequency <= xi_max :
            raise ValueError(
                "control_to_data_frequency must be within the paper's "
                f"[{xi_min}, {xi_max}] range"
            )

        _, kappa_max = self.network.connectivity_range
        highest_assigned_kappa = max(
            index + 1
            for index, count in enumerate(experiment.connectivity_counts)
            if count > 0
        )
        if highest_assigned_kappa > kappa_max :
            raise ValueError("assigned connectivity exceeds the paper's kappa range")

        if highest_assigned_kappa > self.network.maximum_paths :
            raise ValueError("assigned connectivity exceeds maximum_paths")

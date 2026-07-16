"""Paper-traceable implementation of non-uniform k-connectivity for UWSNs."""

from .environment import (
    AcousticEnergyEnvironment,
    Deployment,
    NetworkEnvironment,
    absorption_coefficient_db_per_km,
    build_acoustic_energy_environment,
    build_directed_arcs,
    build_network_environment,
    build_paper_network_environment,
    frequency_component,
    generate_uniform_deployment,
    minimum_link_transmission_energy_j_per_bit,
    pairwise_distances,
    power_level_energies_j_per_bit,
    transmission_energy_j_per_bit,
    transmission_loss,
)
from .params import (
    AcousticParameters,
    ExperimentParameters,
    NetworkParameters,
    PaperParameters,
    PowerLevelTable,
)

__all__ = [
    "AcousticParameters",
    "AcousticEnergyEnvironment",
    "Deployment",
    "ExperimentParameters",
    "NetworkParameters",
    "NetworkEnvironment",
    "PaperParameters",
    "PowerLevelTable",
    "absorption_coefficient_db_per_km",
    "build_acoustic_energy_environment",
    "build_directed_arcs",
    "build_network_environment",
    "build_paper_network_environment",
    "frequency_component",
    "generate_uniform_deployment",
    "minimum_link_transmission_energy_j_per_bit",
    "pairwise_distances",
    "power_level_energies_j_per_bit",
    "transmission_energy_j_per_bit",
    "transmission_loss",
]

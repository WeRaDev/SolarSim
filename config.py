from dataclasses import dataclass

@dataclass
class WeatherConfig:
    location: str

@dataclass
class SolarParkConfig:
    total_capacity: float
    inverter_capacity: float
    performance_ratio: float
    panel_efficiency: float
    temp_coefficient: float
    dust_factor: float
    misc_losses: float
    annual_degradation: float

@dataclass
class BatteryConfig:
    capacity: float
    initial_charge: float
    efficiency: float

@dataclass
class EnergyProfileConfig:
    pumps_power: float
    programmer_power: float
    dosing_pump_power: float
    irrigation_months: list
    staking_nodes: int
    staking_power: float
    cooling_efficiency: float
    gpu_power: float
    gpu_utilization_range: tuple
    num_gpus: int

@dataclass
class SimulationConfig:
    weather: WeatherConfig
    solar_park: SolarParkConfig
    battery: BatteryConfig
    energy_profile: EnergyProfileConfig
    capex: float
    gpu_cost_per_unit: float
    staking_rental_price: float
    gpu_rental_price: float
    year: int

default_config = SimulationConfig(
    weather=WeatherConfig(
        location="Beja, Portugal"
    ),
    solar_park=SolarParkConfig(
        total_capacity=947.52,
        inverter_capacity=800,
        performance_ratio=0.75,
        panel_efficiency=0.2,
        temp_coefficient=-0.0035,
        dust_factor=0.98,
        misc_losses=0.97,
        annual_degradation=0.005
    ),
    battery=BatteryConfig(
        capacity=800,
        initial_charge=250,
        efficiency=0.9
    ),
    energy_profile=EnergyProfileConfig(
        pumps_power=90,
        programmer_power=0.05,
        dosing_pump_power=1,
        irrigation_months=[3, 4, 5, 6, 7, 8, 9],
        staking_nodes=32,
        staking_power=36/24,
        cooling_efficiency=0.4,
        gpu_power=0.7,
        gpu_utilization_range=(0.7, 0.9),
        num_gpus=20        
    ),
    capex=2070500,  # Example value, adjust as needed
    gpu_cost_per_unit=42000,  # Example value
    staking_rental_price=0.3,  # per unit per hour
    gpu_rental_price=2.5,  # per unit per hour
    year = 2023,
)

def load_config(config_file=None):
    if config_file:
        # Load configuration from file
        # This is a placeholder for future implementation
        pass
    return default_config
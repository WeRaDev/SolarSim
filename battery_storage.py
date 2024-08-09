from typing import Dict
from logging_config import log_exceptions, get_logger

class BatteryStorage:
    def __init__(self, capacity: float, initial_charge: float = None, efficiency: float = 0.9):
        self.capacity = capacity
        self.charge = initial_charge if initial_charge is not None else capacity * 0.5
        self.efficiency = efficiency
        self.previous_charge = self.charge
        self.logger = get_logger(self.__class__.__name__)

    def temperature_factor(self, temperature: float) -> float:
        return 1 - 0.005 * abs(temperature - 25)
    @log_exceptions
    def charge_battery(self, energy: float, temperature: float) -> float:
        self.previous_charge = self.charge
        temp_adjusted_capacity = self.capacity * self.temperature_factor(temperature)
        energy_to_store = energy * self.efficiency
        actual_stored = min(energy_to_store, temp_adjusted_capacity - self.charge)
        self.charge += actual_stored
        return actual_stored / self.efficiency
    
    @log_exceptions
    def discharge_battery(self, energy_needed: float, temperature: float) -> float:
        self.previous_charge = self.charge
        temp_adjusted_charge = self.charge * self.temperature_factor(temperature)
        energy_to_discharge = min(energy_needed / self.efficiency, temp_adjusted_charge)
        self.charge -= energy_to_discharge
        return energy_to_discharge * self.efficiency

    def get_daily_data(self) -> Dict[str, float]:
        return {
            'capacity': self.capacity,
            'charge': self.charge,
            'previous_charge': self.previous_charge
        }
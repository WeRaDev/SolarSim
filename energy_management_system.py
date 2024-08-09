import numpy as np
from typing import List, Dict, Any
from logging_config import log_exceptions, get_logger

class EnergyManagementSystem:
    def __init__(self, solar_park, energy_profile, battery):
        self.solar_park = solar_park
        self.energy_profile = energy_profile
        self.battery = battery
        self.logger = get_logger(self.__class__.__name__)
    @log_exceptions    
    def allocate_energy(self, production: float, month: int, hour: int, weather: Dict[str, Any]) -> Dict[str, float]:
        self.logger.debug(f"Allocating energy: production={production}, month={month}, hour={hour}")
        
        # Calculate energy needs
        irrigation_need = self.energy_profile.irrigation_need(month, hour, weather)
        server_need = self.energy_profile.server_power_consumption(hour)
        
        # Initialize allocation dictionary
        allocation = {
            'irrigation': 0,
            'servers': 0,
            'gpu': 0,
            'battery_change': 0,
            'total_consumption': 0,
            'energy_deficit': 0
        }

        remaining_energy = production

        # Priority 1: Servers
        if remaining_energy >= server_need:
            allocation['servers'] = server_need
            remaining_energy -= server_need
        else:
            allocation['servers'] = remaining_energy
            remaining_energy = 0
            allocation['energy_deficit'] += server_need - allocation['servers']
            
        # Priority 2: Irrigation
        if remaining_energy >= irrigation_need:
            allocation['irrigation'] = irrigation_need
            remaining_energy -= irrigation_need
        else:
            allocation['irrigation'] = remaining_energy
            remaining_energy = 0
            allocation['energy_deficit'] += irrigation_need - allocation['irrigation']

        #  Priority 3: GPU (if any left)
        if remaining_energy > 0:
            allocation['gpu'] = self.energy_profile.gpu_power_consumption(remaining_energy)
            remaining_energy -= allocation['gpu']
            
        # Use remaining energy for Battery Charging
        if remaining_energy > 0:
            charged_energy = self.battery.charge_battery(remaining_energy, weather['temperature'])
            allocation['battery_change'] = charged_energy
            remaining_energy -= charged_energy

        # If there's still an energy deficit, try to discharge from battery
        if allocation['energy_deficit'] > 0:
            battery_discharge = self.battery.discharge_battery(allocation['energy_deficit'], weather['temperature'])
            allocation['battery_change'] -= battery_discharge
            allocation['energy_deficit'] -= battery_discharge

        # Calculate total consumption
        allocation['total_consumption'] = sum([allocation['irrigation'], allocation['servers'], allocation['gpu']])

        self.logger.debug(f"Energy allocation result: {allocation}")
        return allocation

    def get_daily_allocation(self, day: int, weather_data: Dict[str, List[float]]) -> List[Dict[str, float]]:
        month = self._get_month(day)
        daily_allocation = []
        for hour in range(24):
            weather = {key: weather_data[key][hour] for key in weather_data}
            production = self.solar_park.calculate_hourly_energy(weather)
            allocation = self.allocate_energy(production, month, hour, weather)
            daily_allocation.append(allocation)
        return daily_allocation

    @staticmethod
    def _get_month(day: int) -> int:
        return np.searchsorted(np.cumsum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]), day + 1)
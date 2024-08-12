from typing import List, Dict, Any
from logging_config import log_exceptions, get_logger
from solar_park_simulator import SolarParkSimulator
from energy_profile import EnergyProfile
from battery_storage import BatteryStorage
from helper import DateHelper

class EnergyManagementSystem:
    def __init__(self, solar_park: SolarParkSimulator, energy_profile: EnergyProfile, battery: BatteryStorage):
        self.solar_park = solar_park
        self.energy_profile = energy_profile
        self.battery = battery
        self.logger = get_logger(self.__class__.__name__)
        self.irrigation_hours = 0
        
    @log_exceptions    
    def allocate_energy(self, production: float, month: int, hour: int, weather: Dict[str, Any]) -> Dict[str, float]:
        self.logger.debug(f"Allocating energy: production={production}, month={month}, hour={hour}")
        if hour == 0:
            self.irrigation_hours = 0
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
            '_energy_deficit': 0
        }

        remaining_energy = production

        # Priority 1: Servers
        if remaining_energy >= server_need:
            allocation['servers'] = server_need
            remaining_energy -= server_need
        else:
            allocation['servers'] = remaining_energy
            remaining_energy = 0
            allocation['_energy_deficit'] += server_need - allocation['servers']
            if allocation['_energy_deficit'] > 0:
                battery_discharge = self.battery.discharge_battery(allocation['_energy_deficit'], weather['temperature'])
                allocation['servers'] += battery_discharge
                allocation['battery_change'] -= battery_discharge
            
        # Priority 2: Irrigation (if any energy left and irrigation conditions met)
        if remaining_energy > 0 and self.irrigation_hours < 8:
            irrigation_need = self.energy_profile.irrigation_need(month, hour, weather)
            if irrigation_need > 0:
                if remaining_energy >= irrigation_need:
                    allocation['irrigation'] = irrigation_need
                    remaining_energy -= irrigation_need
                    self.irrigation_hours += 1
                else:
                    allocation['irrigation'] = 0

        # Priority 3: GPU (if any left)
        if remaining_energy > 0:
            allocation['gpu'] = self.energy_profile.gpu_power_consumption(remaining_energy)
            remaining_energy -= allocation['gpu']
        else:
            # Allocate acceptable discharge equal to hourly discharge rate for 18 hours autonomy
            acceptable_discharge = (self.battery.capacity - server_need * 24) / 12        
            if self.battery.charge > acceptable_discharge + server_need:
                # allocates GPUs to use all acceptable discharge
                allocation['gpu'] = self.energy_profile.gpu_power_consumption(acceptable_discharge)
                allocation['battery_change'] -= self.battery.discharge_battery(allocation['gpu'], weather['temperature'])
                
        # Use remaining energy for Battery Charging
        if remaining_energy > 0:
            charged_energy = self.battery.charge_battery(remaining_energy, weather['temperature'])
            allocation['battery_change'] = charged_energy
            remaining_energy -= charged_energy

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
        return DateHelper.get_month(day)

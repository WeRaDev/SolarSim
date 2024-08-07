import numpy as np
from numba import jit
import matplotlib.pyplot as plt
from typing import List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from matplotlib.dates import DateFormatter
from collections import defaultdict
import math
from logging_config import log_exceptions, get_logger
from weather_simulator import WeatherSimulator
from config import WeatherConfig, SolarParkConfig, BatteryConfig, EnergyProfileConfig, SimulationConfig

class SolarParkSimulator:
    def __init__(self, location, total_capacity, inverter_capacity, performance_ratio):
        self.logger = get_logger(self.__class__.__name__)
        self.location = location
        self.total_capacity = total_capacity
        self.inverter_capacity = inverter_capacity
        self.performance_ratio = performance_ratio
        self.weather_simulator = WeatherSimulator(location)
        
        # Panel specifications
        self.panel_efficiency = 0.2
        self.temp_coefficient = -0.0035
        self.dust_factor = 0.98
        self.misc_losses = 0.97
        self.annual_degradation = 0.005
        self.years_in_operation = 0

    @log_exceptions
    def calculate_hourly_energy(self, weather):
        return self._calculate_hourly_energy_optimized(
            self.total_capacity, self.inverter_capacity, self.performance_ratio,
            self.panel_efficiency, self.temp_coefficient, self.dust_factor,
            self.misc_losses, self.annual_degradation, self.years_in_operation,
            weather['sun_intensity'], weather['temperature'], weather['humidity'],
            weather['cloud_cover'], weather['wind_speed'], weather['is_raining']
        )

    @staticmethod
    @jit(nopython=True)
    def _calculate_hourly_energy_optimized(total_capacity, inverter_capacity, performance_ratio,
                                           panel_efficiency, temp_coefficient, dust_factor,
                                           misc_losses, annual_degradation, years_in_operation,
                                           sun_intensity, temperature, humidity,
                                           cloud_cover, wind_speed, is_raining):
        degradation_factor = (1 - annual_degradation) ** years_in_operation
        base_energy = total_capacity * sun_intensity * performance_ratio * degradation_factor

        temp_adjustment = 1 + temp_coefficient * (temperature - 25)
        humidity_adjustment = 1 - (humidity - 50) * 0.001
        cloud_adjustment = 1 - 0.75 * cloud_cover
        wind_cooling = 1 + 0.001 * wind_speed
        rain_adjustment = 0.9 if is_raining else 1

        energy_produced = (base_energy * temp_adjustment * humidity_adjustment * 
                           cloud_adjustment * wind_cooling * rain_adjustment * 
                           dust_factor * misc_losses)

        inverter_efficiency = min(0.9 + 0.05 * (energy_produced / inverter_capacity), 0.98)
        return min(energy_produced * inverter_efficiency, inverter_capacity)
        
    def simulate_annual_production(self) -> Dict[str, Any]:
        self.logger.info("Starting annual simulation")
        weather_data = self.weather_simulator.simulate_year()
        hourly_production = np.array([self.calculate_hourly_energy(hour) for hour in weather_data])
        total_annual_production = np.sum(hourly_production)
        specific_yield = total_annual_production / self.total_capacity
        self.logger.info("Complete annual simulation")
        return {
            'energy_production': hourly_production,
            'weather_data': weather_data,
            'total_annual_production': total_annual_production,
            'specific_yield': specific_yield
        }

    def get_daily_production(self, weather_data: Dict[str, List[float]]) -> List[float]:
        return [self.calculate_hourly_energy(
            {key: weather_data[key][i] for key in weather_data}
        ) for i in range(24)]
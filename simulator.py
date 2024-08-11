from solar_park_simulator import SolarParkSimulator
from energy_profile import EnergyProfile
from battery_storage import BatteryStorage
from energy_management_system import EnergyManagementSystem
from weather_simulator import WeatherSimulator
from datetime import datetime, timedelta
import pandas as pd
import csv
import os
from logging_config import setup_logging, log_exceptions, get_logger
import logging
from reporting import generate_report_off_grid
from config import load_config, SimulationConfig
from typing import Dict, Any, List, Any
from helper import DateHelper

class Simulator:
    def __init__(self, config: SimulationConfig):
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info("Initializing Simulator")
        self.config = config
        self.weather_simulator = WeatherSimulator(config.weather.location, config.year)
        self.solar_park = SolarParkSimulator(
            weather_simulator=self.weather_simulator,
            total_capacity=config.solar_park.total_capacity,
            inverter_capacity=config.solar_park.inverter_capacity,
            performance_ratio=config.solar_park.performance_ratio
        )
        self.energy_profile = EnergyProfile(config.energy_profile)
        self.battery = BatteryStorage(
            capacity=config.battery.capacity,
            initial_charge=config.battery.initial_charge,
            efficiency=config.battery.efficiency
        )
        self.ems = EnergyManagementSystem(self.solar_park, self.energy_profile, self.battery)
        self.data_file = os.path.join('data', 'simulation_data.csv')
        self.ensure_data_directory()
        
    def ensure_data_directory(self):
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)

    @log_exceptions
    def run_annual_simulation(self) -> List[Dict[str, Any]]:
        self.logger.info("Starting annual simulation")
        results = []
        with open(self.data_file, 'w', newline='') as csvfile:
            fieldnames = ['datetime', 'sun_intensity', 'temperature', 'humidity', 
                          'is_raining', 'cloud_cover', 'wind_speed',
                          'production', 'irrigation', 'servers', 'gpu', 'battery_change',
                          'total_consumption', 'battery_charge', 'energy_deficit']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for day in range(DateHelper.get_days(self.config.year)):
                daily_results = self._run_daily_simulation(day)
                results.extend(daily_results)
                for result in daily_results:
                    writer.writerow(result)
        
        self.logger.info("Completed annual simulation")
        return results

    def _run_daily_simulation(self, day: int) -> List[Dict[str, Any]]:
        daily_results = []
        for hour in range(24):
            result = self._run_hourly_simulation(day, hour)
            daily_results.append(result)
        return daily_results

    def _run_hourly_simulation(self, day: int, hour: int) -> Dict[str, Any]:
        month = self._get_month(day)
        weather = self.solar_park.weather_simulator.simulate_hour(day + 1, hour)
        production = self.solar_park.calculate_hourly_energy(weather)
        allocation = self.ems.allocate_energy(production, month, hour, weather)
        energy_deficit = max(0, allocation['total_consumption'] - production - allocation['battery_change'])
        
        step_data = {
            'datetime': datetime(self.config.year, 1, 1) + timedelta(days=day, hours=hour),
            'sun_intensity': weather['sun_intensity'],
            'temperature': weather['temperature'],
            'humidity': weather['humidity'],
            'is_raining': weather['is_raining'],
            'cloud_cover': weather['cloud_cover'],
            'wind_speed': weather['wind_speed'],
            'production': production,
            'irrigation': allocation['irrigation'],
            'servers': allocation['servers'],
            'gpu': allocation['gpu'],
            'battery_change': allocation['battery_change'],
            'total_consumption': allocation['total_consumption'],
            'battery_charge': self.battery.charge,
            'energy_deficit': energy_deficit
        }
        
        self._validate_simulation_step(step_data)
        return step_data

    def _get_month(self, day: int):
        return DateHelper.get_month(day)

    def _validate_simulation_step(self, step_data: Dict[str, Any]):
        if step_data['production'] < 0:
            self.logger.warning(f"Negative energy production: {step_data['production']} at {step_data['datetime']}")
        if step_data['total_consumption'] < 0:
            self.logger.warning(f"Negative energy consumption: {step_data['total_consumption']} at {step_data['datetime']}")
        if step_data['battery_charge'] < 0:
            self.logger.warning(f"Negative battery charge: {step_data['battery_charge']} at {step_data['datetime']}")
        if step_data['total_consumption'] == 0:
            self.logger.info(f"Zero consumption at {step_data['datetime']}")
        if step_data['production'] == 0 and step_data['sun_intensity'] > 0:
            self.logger.info(f"Zero production with non-zero sun intensity at {step_data['datetime']}")

    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        df_results = pd.DataFrame(results)
        
        total_production = df_results['production'].sum()
        total_consumption = df_results['total_consumption'].sum()
        average_battery_charge = df_results['battery_charge'].mean()
        total_energy_deficit = df_results['energy_deficit'].sum()

        # Calculate revenues
        staking_revenue = df_results['servers'].sum() * self.config.staking_rental_price
        gpu_revenue = df_results['gpu'].sum() * self.config.gpu_rental_price
        total_revenue = staking_revenue + gpu_revenue

        # ROI Analysis
        total_revenue_7years = total_revenue * 7
        profit_7years = total_revenue_7years - self.config.capex
        roi_7years = (profit_7years / self.config.capex) * 100
        payback_period = self.config.capex / total_revenue

        results_summary = {
            'hourly_production': df_results['production'].values,
            'hourly_consumption': {
                'total': df_results['total_consumption'].values,
                'farm_irrigation': df_results['irrigation'].values,
                'data_center': df_results['servers'].values + df_results['gpu'].values
            },
            'battery_charge': df_results['battery_charge'].values,
            'energy_deficit': df_results['energy_deficit'].values,
            'total_annual_production': total_production,
            'total_annual_consumption': total_consumption,
            'average_battery_charge': average_battery_charge,
            'total_energy_deficit': total_energy_deficit,
            'specific_yield': total_production / self.solar_park.total_capacity,
            'annual_revenue': {
                'staking': staking_revenue,
                'gpu_rental': gpu_revenue,
                'total': total_revenue
            },
            'roi_analysis': {
                'total_revenue_7years': total_revenue_7years,
                'profit_7years': profit_7years,
                'roi_7years': roi_7years,
                'payback_period': payback_period
            }
        }

        return results_summary

def main():
    logger = setup_logging(file_level=logging.DEBUG, console_level=logging.WARNING)
    logger.debug("Logging initialized")
    logger.info("Starting simulation")
    logger.warning("This is a warning message")

    # Create simulator
    config = load_config()
    simulator = Simulator(config)

    # Run simulation
    results = simulator.run_annual_simulation()
    
    # Generate report
    results_summary = simulator.generate_report(results)

    # Generate and print report
    generate_report_off_grid(results_summary, simulator.solar_park, simulator.battery)

if __name__ == "__main__":
    main()
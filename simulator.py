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
            fieldnames = ['datetime', 'ghi', 'dni', 'temperature', 'humidity', 
              'is_raining', 'cloud_cover', 'wind_speed',
              'production', 'irrigation', 'servers', 'gpu', 'battery_change',
              'total_consumption', 'battery_charge', 'energy_deficit', 'extra_energy']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for day in range(DateHelper.get_days(self.config.year)):
                daily_results = self._run_daily_simulation(day)
                results.extend(daily_results)
                for result in daily_results:
                    writer.writerow(result)
        
        total_production = sum(result['production'] for result in results)
        total_consumption = sum(result['total_consumption'] for result in results)
        total_extra_energy = sum(result['extra_energy'] for result in results)
        self.logger.info(f"Annual simulation completed. Total production: {total_production:.2f} kWh, "
                         f"Total consumption: {total_consumption:.2f} kWh, "
                         f"Total extra energy: {total_extra_energy:.2f} kWh")
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
        #energy_deficit = max(0, allocation['total_consumption'] - production - allocation['battery_change'])
        extra_energy = production - allocation['total_consumption'] - allocation['battery_change']
        
        step_data = {
            'datetime': datetime(self.config.year, 1, 1) + timedelta(days=day, hours=hour),
            'ghi': weather['ghi'],
            'dni': weather['dni'],
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
            'energy_deficit': allocation['_energy_deficit'],
            'extra_energy': max(0, extra_energy)  # Ensure extra energy is non-negative
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
        if step_data['production'] == 0 and (step_data['ghi'] > 0 or step_data['dni'] > 0):
            self.logger.info(f"Zero production with non-zero irradiance at {step_data['datetime']}")


    def generate_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        df_results = pd.DataFrame(results)
        
        # Ensure 'datetime' is a datetime type and set it as the index
        df_results['datetime'] = pd.to_datetime(df_results['datetime'])
        df_results.set_index('datetime', inplace=True)
        
        total_production = df_results['production'].sum()
        total_consumption = df_results['total_consumption'].sum()
        average_battery_charge = df_results['battery_charge'].mean()
        total_energy_deficit = df_results['energy_deficit'].sum()
    
        # Calculate revenues
        staking_revenue = df_results['servers'].sum() * self.config.staking_rental_price
        gpu_revenue = df_results['gpu'].sum() * self.config.gpu_rental_price
        total_revenue = staking_revenue + gpu_revenue
        roi = (total_revenue / (self.config.capex + self.config.num_gpus * self.config.gpu_cost_per_unit)) * 100
    
        # ROI Analysis
        total_revenue_7years = total_revenue * 7
        capex = (self.config.capex + self.config.num_gpus * self.config.gpu_cost_per_unit)
        profit_7years = total_revenue_7years - capex
        roi_7years = (profit_7years / capex) * 100
        payback_period = capex / total_revenue
    
        results_summary = {
            'hourly_production': df_results['production'].values,
            'hourly_consumption': {
                'total': df_results['total_consumption'].values,
                'farm_irrigation': df_results['irrigation'].values,
                'servers': df_results['servers'].values,
                'gpu': df_results['gpu'].values,
                'data_center': df_results['servers'].values + df_results['gpu'].values
            },
            'battery_charge': df_results['battery_charge'].values,
            'energy_deficit': df_results['energy_deficit'].values,
            'total_annual_production': total_production,
            'total_annual_consumption': total_consumption,
            'total_extra_energy': df_results['extra_energy'].sum(),
            'average_battery_charge': average_battery_charge,
            'total_energy_deficit': total_energy_deficit,
            'specific_yield': total_production / self.solar_park.total_capacity,
            'annual_revenue': {
                'staking': staking_revenue,
                'gpu_rental': gpu_revenue,
                'total': total_revenue,
                'ROI': roi
            },
            'roi_analysis': {
                'capex': capex,
                'total_revenue_7years': total_revenue_7years,
                'profit_7years': profit_7years,
                'roi_7years': roi_7years,
                'payback_period': payback_period
            }
        }
    
        # Calculate daily totals
        results_summary['daily_production'] = df_results.groupby(df_results.index.date)['production'].sum().tolist()
        results_summary['daily_consumption'] = df_results.groupby(df_results.index.date)['total_consumption'].sum().tolist()
        results_summary['daily_deficit'] = df_results.groupby(df_results.index.date)['energy_deficit'].sum().tolist()
        
        results_summary['peak_production'] = df_results['production'].max()
        results_summary['peak_consumption'] = df_results['total_consumption'].max()
        
        results_summary['capacity_factor'] = (total_production / (self.solar_park.total_capacity * 8760)) * 100
    
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
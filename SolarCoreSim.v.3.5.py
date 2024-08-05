import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from matplotlib.dates import DateFormatter
from collections import defaultdict
import math
import logging
logging.basicConfig(level=logging.WARNING)

class WeatherSimulator:
    def __init__(self, location: str):
        self.location = location
        self.monthly_data = {
            'sun_hours': [7.18, 9.18, 10.07, 11.52, 13.34, 13.89, 14.0, 13.56, 11.19, 8.85, 7.38, 7.33],
            'temp': [10.45, 11.05, 13.47, 16.43, 21.09, 24.92, 27.79, 28.1, 25.4, 20.63, 14.55, 11.62],
            'humidity': [80.81, 78.19, 77.66, 73.91, 60.69, 52.84, 48.86, 47.07, 51.93, 60.7, 73.48, 76.96],
            'precipitation': [24.16, 27.53, 36.22, 41.97, 26.91, 6.36, 1.76, 2.97, 16.72, 40.79, 41.49, 25.15],
            'precipitation_days': [5.91, 5.45, 7.64, 7.91, 4.55, 1.36, 0.64, 1.0, 3.0, 5.0, 7.45, 4.36],
            'cloud_cover': [0.6, 0.55, 0.5, 0.45, 0.3, 0.2, 0.1, 0.15, 0.3, 0.45, 0.55, 0.6],
            'wind_speed': [4.5, 4.8, 5.2, 5.5, 5.0, 4.8, 4.5, 4.3, 4.0, 4.2, 4.5, 4.7]
        }
        self.days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    def simulate_hour(self, day_of_year: int, hour: int) -> Dict[str, Any]:
        month = next(m for m, days in enumerate(self._cumulative_days()) if day_of_year <= days) - 1
        
        # Interpolate daily values from monthly data
        sun_hours = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['sun_hours'])
        base_temp = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['temp'])
        humidity = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['humidity'])
        precipitation_prob = self.monthly_data['precipitation_days'][month] / self.days_in_month[month]
        cloud_cover = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['cloud_cover'])
        wind_speed = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['wind_speed'])

        # Simulate hourly variations
        hour_angle = (hour - 12) * 15  # Solar hour angle
        sun_intensity = max(0, np.cos(np.radians(hour_angle))) * (sun_hours / 12)  # Adjust for actual sun hours
        
        # More sophisticated temperature model
        temp = base_temp + 5 * sun_intensity - 2 * cloud_cover + np.random.normal(0, 1)
        
        # More sophisticated humidity model
        humidity = humidity - 10 * sun_intensity + 20 * cloud_cover + np.random.normal(0, 5)
        humidity = np.clip(humidity, 0, 100)
        
        # Simplified precipitation model
        is_raining = np.random.random() < precipitation_prob

        return {
            'sun_intensity': sun_intensity,
            'temperature': temp,
            'humidity': humidity,
            'is_raining': is_raining,
            'cloud_cover': cloud_cover,
            'wind_speed': wind_speed
        }

    def simulate_year(self) -> List[Dict[str, Any]]:
        hourly_weather = []
        for day in range(365):
            for hour in range(24):
                hour_weather = self.simulate_hour(day + 1, hour)
                hourly_weather.append(hour_weather)
        return hourly_weather

    def _cumulative_days(self) -> List[int]:
        return [sum(self.days_in_month[:i+1]) for i in range(12)]

    def _mid_month_days(self) -> List[int]:
        cum_days = [0] + self._cumulative_days()
        return [(cum_days[i] + cum_days[i+1]) // 2 for i in range(12)]

    def get_daily_data(self, day: int) -> Dict[str, List[float]]:
        daily_data = {
            'sun_intensity': [], 'temperature': [], 'humidity': [],
            'is_raining': [], 'cloud_cover': [], 'wind_speed': []
        }
        for hour in range(24):
            weather = self.simulate_hour(day + 1, hour)
            for key in daily_data:
                daily_data[key].append(weather[key])
        return daily_data

class SolarParkSimulator:
    def __init__(self, location: str, total_capacity: float, inverter_capacity: float, performance_ratio: float):
        self.location = location
        self.total_capacity = total_capacity  # kWp
        self.inverter_capacity = inverter_capacity  # kWn
        self.performance_ratio = performance_ratio
        self.weather_simulator = WeatherSimulator(location)
        
        # Panel specifications
        self.panel_efficiency = 0.2  # 20% efficiency
        self.temp_coefficient = -0.0035  # -0.35% per degree Celsius above 25°C
        self.dust_factor = 0.98  # 2% loss due to dust/soiling
        self.misc_losses = 0.97  # 3% miscellaneous losses (wiring, connections, etc.)
        self.annual_degradation = 0.005
        self.years_in_operation = 0  # This should be updated each year in a multi-year simulation

    def calculate_hourly_energy(self, weather: Dict[str, Any]) -> float:
        degradation_factor = (1 - self.annual_degradation) ** self.years_in_operation
        base_energy = self.total_capacity * weather['sun_intensity'] * self.performance_ratio * degradation_factor

        # Apply adjustments
        temp_adjustment = 1 + self.temp_coefficient * (weather['temperature'] - 25)
        humidity_adjustment = 1 - (weather['humidity'] - 50) * 0.001
        cloud_adjustment = 1 - 0.75 * weather['cloud_cover']  # Simplified cloud impact
        wind_cooling = 1 + 0.001 * weather['wind_speed']  # Wind cooling effect
        rain_adjustment = 0.9 if weather['is_raining'] else 1

        energy_produced = (base_energy * temp_adjustment * humidity_adjustment * 
                           cloud_adjustment * wind_cooling * rain_adjustment * 
                           self.dust_factor * self.misc_losses)
        # Cap at inverter capacity
        inverter_efficiency = 0.9 + 0.05 * (energy_produced / self.inverter_capacity)
        inverter_efficiency = min(inverter_efficiency, 0.98)  # Cap at 98% efficiency
        return min(energy_produced * inverter_efficiency, self.inverter_capacity)
        
    def simulate_annual_production(self) -> Dict[str, Any]:
        weather_data = self.weather_simulator.simulate_year()
        hourly_production = np.array([self.calculate_hourly_energy(hour) for hour in weather_data])
        total_annual_production = np.sum(hourly_production)
        specific_yield = total_annual_production / self.total_capacity

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

class EnergyProfile:
    def __init__(self):
        # Farm-related attributes
        self.pumps_power = 90  # kW
        self.programmer_power = 0.05  # kW
        self.dosing_pump_power = 1  # kW
        
        # Irrigation months (march to october, 0-indexed)
        self.irrigation_months = [3, 4, 5, 6, 7, 8, 9]
        self.days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

        # Data center attributes
        self.fixed_consumers = {
            "Starlink internet": 0.1,  # kW
            "Monitoring system": 0.05,  # kW
            "Lighting and auxiliary": 0.2  # kW
        }
        self.staking_nodes = 16
        self.staking_power = 12 / 24  # kWh per hour
        self.cooling_efficiency = 0.4
        self.gpu_power = 0.7  # kW
        self.gpu_utilization_range = (0.7, 0.9)
        self.num_gpus = 20
        # Debugging attributes
        self.debug_data = defaultdict(lambda: defaultdict(float))

    def server_power_consumption(self, hour: int) -> float:
        base_load = self.staking_power * self.staking_nodes
        time_factor = 1 + 0.2 * math.sin(hour * math.pi / 12)  # Daily variation
        return base_load * time_factor

    def gpu_power_consumption(self, available_energy: float) -> float:
        max_gpu_power = self.gpu_power * self.num_gpus
        utilization = min(1, available_energy / max_gpu_power)
        return max_gpu_power * utilization

    def irrigation_need(self, month: int, hour: int, weather: Dict[str, Any]) -> float:
        if month in self.irrigation_months and not weather['is_raining']:
            return self.pumps_power + self.dosing_pump_power + self.programmer_power
        return 0

    def hourly_consumption(self, month: int, hour: int, weather: Dict[str, Any], available_energy: float) -> Dict[str, float]:
        irrigation_consumption = self.irrigation_need(month, hour, weather)
        server_consumption = self.server_power_consumption(hour)
        remaining_energy = available_energy - irrigation_consumption - server_consumption
        gpu_consumption = self.gpu_power_consumption(max(0, remaining_energy))
    
        total_consumption = irrigation_consumption + server_consumption + gpu_consumption
    
        # Update debug data
        self.debug_data[month]['irrigation_hours'] += 1 if irrigation_consumption > 0 else 0
        self.debug_data[month]['irrigation_consumption'] += irrigation_consumption
        self.debug_data[month]['dc_consumption'] += server_consumption + gpu_consumption
        self.debug_data[month]['total_consumption'] += total_consumption
        self.debug_data[month]['rainy_hours'] += 1 if weather['is_raining'] else 0
    
        return {
            'farm_irrigation': irrigation_consumption,
            'data_center': server_consumption,
            'gpu': gpu_consumption,
            'total': total_consumption
        }

    def annual_consumption(self, weather_data: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        farm_irrigation = np.zeros(8760)
        data_center = np.zeros(8760)
        total = np.zeros(8760)

        for hour, weather in enumerate(weather_data):
            day = hour // 24
            month = next(m for m, days in enumerate(np.cumsum(self.days_in_month)) if day < days)
            hour_of_day = hour % 24
            
            # Assume maximum available energy for consumption calculation
            # This will be adjusted later in the energy management system
            max_available_energy = float('inf')
            
            consumption = self.hourly_consumption(month, hour_of_day, weather, max_available_energy)
            
            farm_irrigation[hour] = consumption['farm_irrigation']
            data_center[hour] = consumption['data_center']
            total[hour] = consumption['total']

        return {
            'farm_irrigation': farm_irrigation,
            'data_center': data_center,
            'total': total
        }

    def generate_debug_report(self) -> str:
        report = "Energy Consumption Debug Report\n"
        report += "=" * 40 + "\n\n"
    
        total_irrigation_consumption = 0
        total_dc_consumption = 0
        total_consumption = 0
        total_irrigation_hours = 0
        total_rainy_hours = 0
    
        for month in range(12):
            month_name = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month]
            report += f"Month: {month_name}\n"
            report += f"  Irrigation Hours: {self.debug_data[month]['irrigation_hours']}\n"
            report += f"  Irrigation Consumption: {self.debug_data[month]['irrigation_consumption']:.2f} kWh\n"
            report += f"  Data Center Consumption: {self.debug_data[month]['dc_consumption']:.2f} kWh\n"
            report += f"  Total Consumption: {self.debug_data[month]['total_consumption']:.2f} kWh\n"
            report += f"  Rainy Hours: {self.debug_data[month]['rainy_hours']}\n"
            report += "\n"
    
            total_irrigation_consumption += self.debug_data[month]['irrigation_consumption']
            total_dc_consumption += self.debug_data[month]['dc_consumption']
            total_consumption += self.debug_data[month]['total_consumption']
            total_irrigation_hours += self.debug_data[month]['irrigation_hours']
            total_rainy_hours += self.debug_data[month]['rainy_hours']
    
        report += "Annual Totals\n"
        report += "=" * 40 + "\n"
        report += f"Total Irrigation Hours: {total_irrigation_hours}\n"
        report += f"Total Irrigation Consumption: {total_irrigation_consumption:.2f} kWh\n"
        report += f"Total Data Center Consumption: {total_dc_consumption:.2f} kWh\n"
        report += f"Total Energy Consumption: {total_consumption:.2f} kWh\n"
        report += f"Total Rainy Hours: {total_rainy_hours}\n"
    
        return report

    def get_daily_consumption(self, day: int, weather_data: Dict[str, List[float]], available_energy: List[float]) -> Dict[str, List[float]]:
        month = next(m for m, days in enumerate(np.cumsum(self.days_in_month)) if day < days)
        daily_consumption = {
            'farm_irrigation': [], 'data_center': [], 'gpu': [], 'total': []
        }
        for hour in range(24):
            weather = {key: weather_data[key][hour] for key in weather_data}
            consumption = self.hourly_consumption(month, hour, weather, available_energy[hour])
            daily_consumption['farm_irrigation'].append(consumption['farm_irrigation'])
            daily_consumption['data_center'].append(consumption['data_center'])
            daily_consumption['gpu'].append(consumption['gpu'])
            daily_consumption['total'].append(consumption['total'])
        return daily_consumption

    def generate_debug_report(self) -> str:
        report = "Energy Consumption Debug Report\n"
        report += "=" * 40 + "\n\n"

        total_irrigation_consumption = 0
        total_dc_consumption = 0
        total_consumption = 0
        total_irrigation_hours = 0
        total_rainy_hours = 0

        for month in range(12):
            month_name = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month]
            report += f"Month: {month_name}\n"
            report += f"  Irrigation Hours: {self.debug_data[month]['irrigation_hours']}\n"
            report += f"  Irrigation Consumption: {self.debug_data[month]['irrigation_consumption']:.2f} kWh\n"
            report += f"  Data Center Consumption: {self.debug_data[month]['dc_consumption']:.2f} kWh\n"
            report += f"  Total Consumption: {self.debug_data[month]['total_consumption']:.2f} kWh\n"
            report += f"  Rainy Hours: {self.debug_data[month]['rainy_hours']}\n"
            report += "\n"

            total_irrigation_consumption += self.debug_data[month]['irrigation_consumption']
            total_dc_consumption += self.debug_data[month]['dc_consumption']
            total_consumption += self.debug_data[month]['total_consumption']
            total_irrigation_hours += self.debug_data[month]['irrigation_hours']
            total_rainy_hours += self.debug_data[month]['rainy_hours']

        report += "Annual Totals\n"
        report += "=" * 40 + "\n"
        report += f"Total Irrigation Hours: {total_irrigation_hours}\n"
        report += f"Total Irrigation Consumption: {total_irrigation_consumption:.2f} kWh\n"
        report += f"Total Data Center Consumption: {total_dc_consumption:.2f} kWh\n"
        report += f"Total Energy Consumption: {total_consumption:.2f} kWh\n"
        report += f"Total Rainy Hours: {total_rainy_hours}\n"

        return report

class BatteryStorage:
    def __init__(self, capacity: float):
        self.capacity = capacity
        self.charge = capacity * 0.5
        self.efficiency = 0.9
        self.previous_charge = self.charge

    def temperature_factor(self, temperature: float) -> float:
        return 1 - 0.005 * abs(temperature - 25)

    def charge_battery(self, energy: float, temperature: float) -> float:
        self.previous_charge = self.charge
        temp_adjusted_capacity = self.capacity * self.temperature_factor(temperature)
        energy_to_store = energy * np.sqrt(self.efficiency)
        actual_stored = min(energy_to_store, temp_adjusted_capacity - self.charge)
        self.charge += actual_stored
        return actual_stored / np.sqrt(self.efficiency)

    def discharge_battery(self, energy_needed: float, temperature: float) -> float:
        self.previous_charge = self.charge
        temp_adjusted_charge = self.charge * self.temperature_factor(temperature)
        energy_to_discharge = min(energy_needed / np.sqrt(self.efficiency), temp_adjusted_charge)
        self.charge -= energy_to_discharge
        return energy_to_discharge * np.sqrt(self.efficiency)

    def get_daily_data(self) -> Dict[str, float]:
        return {
            'capacity': self.capacity,
            'charge': self.charge,
            'previous_charge': self.previous_charge
        }

class EnergyManagementSystem:
    def __init__(self, solar_park: SolarParkSimulator, energy_profile: EnergyProfile, battery: BatteryStorage):
        self.solar_park = solar_park
        self.energy_profile = energy_profile
        self.battery = battery

    def allocate_energy(self, production: float, month: int, hour: int, weather: Dict[str, Any]) -> Dict[str, float]:
        irrigation_need = self.energy_profile.irrigation_need(month, hour, weather)
        server_need = self.energy_profile.server_power_consumption(hour)
        available_for_gpu = production - irrigation_need - server_need
        
        if available_for_gpu > 0:
            gpu_consumption = self.energy_profile.gpu_power_consumption(available_for_gpu)
            excess_energy = available_for_gpu - gpu_consumption
            if excess_energy > 0:
                self.battery.charge_battery(excess_energy, weather['temperature'])
        else:
            gpu_consumption = 0
            deficit = -available_for_gpu
            battery_discharge = self.battery.discharge_battery(deficit, weather['temperature'])
            if battery_discharge < deficit:
                # Handle energy shortage (e.g., reduce non-critical loads)
                pass

        return {
            'irrigation': irrigation_need,
            'servers': server_need,
            'gpu': gpu_consumption,
            'battery_change': self.battery.charge - self.battery.previous_charge,
            'total_consumption': irrigation_need + server_need + gpu_consumption
        }

    def get_daily_allocation(self, day: int, weather_data: Dict[str, List[float]]) -> List[Dict[str, float]]:
        month = next(m for m, days in enumerate(np.cumsum(self.energy_profile.days_in_month)) if day < days)
        daily_allocation = []
        for hour in range(24):
            weather = {key: weather_data[key][hour] for key in weather_data}
            production = self.solar_park.calculate_hourly_energy(weather)
            allocation = self.allocate_energy(production, month, hour, weather)
            daily_allocation.append(allocation)
        return daily_allocation

def simulate_off_grid(hourly_production: np.ndarray, hourly_consumption: np.ndarray, battery: BatteryStorage) -> Dict[str, np.ndarray]:
    battery_charge = np.zeros(len(hourly_production))
    energy_deficit = np.zeros(len(hourly_production))
    
    for hour in range(len(hourly_production)):
        net_energy = hourly_production[hour] - hourly_consumption[hour]
        
        if net_energy > 0:
            # Excess energy: charge battery
            battery.charge_battery(net_energy)
        else:
            # Energy deficit: discharge battery
            energy_from_battery = battery.discharge_battery(-net_energy)
            if energy_from_battery < -net_energy:
                energy_deficit[hour] = -net_energy - energy_from_battery
        
        battery_charge[hour] = battery.charge

    return {
        'battery_charge': battery_charge,
        'energy_deficit': energy_deficit,
        'total_consumption': hourly_consumption
    }
def plot_energy_production(results: Dict[str, Any]):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))

    # Daily production
    ax1.plot(results['daily_production'])
    ax1.set_title('Daily Energy Production')
    ax1.set_xlabel('Day of Year')
    ax1.set_ylabel('Energy (kWh)')

    # Monthly production
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ax2.bar(months, results['monthly_production'])
    ax2.set_title('Monthly Energy Production')
    ax2.set_xlabel('Month')
    ax2.set_ylabel('Energy (kWh)')
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.show()
    
def plot_energy_balance_off_grid(results: Dict[str, Any]):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 16))

    # Hourly energy flow
    hours = np.arange(len(results['daily_production']))
    ax1.plot(hours, results['daily_production'], label='Production', color='green', alpha=0.7)
    ax1.plot(hours, results['total_consumption'], label='Consumption', color='red', alpha=0.7)
    ax1.set_title('Hourly Energy Production and Consumption')
    ax1.set_xlabel('Hour of Year')
    ax1.set_ylabel('Energy (kWh)')
    ax1.legend()

    # Battery charge level
    ax2.plot(hours, results['battery_charge'], label='Battery Charge', color='purple')
    ax2.set_title('Hourly Battery Charge Level')
    ax2.set_xlabel('Hour of Year')
    ax2.set_ylabel('Energy (kWh)')
    ax2.set_ylim(0, results['battery_charge'].max() * 1.1)
    ax2.legend()

    plt.tight_layout()
    plt.show()

def plot_energy_balance(results: Dict[str, Any]):
    dates = pd.date_range(start='2023-01-01', periods=8760, freq='h')
    df = pd.DataFrame({
        'Production': results['hourly_production'],
        'Consumption': results['hourly_consumption']['total']
    }, index=pd.date_range(start='2023-01-01', periods=8760, freq='h'))
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
    
    # Yearly plot
    df.resample('D').sum().plot(ax=ax1)
    ax1.set_title('Daily Energy Production and Consumption (Yearly)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Energy (kWh)')
    ax1.legend()

    # Monthly plot (using Aug-Sept as an example)
    july_data = df['2023-08-15':'2023-09-15']
    july_data.plot(ax=ax2)
    ax2.set_title('Hourly Energy Production and Consumption (July)')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Energy (kWh)')
    ax2.legend()
    ax2.xaxis.set_major_formatter(DateFormatter('%d-%b'))

    plt.tight_layout()
    plt.show()

def plot_energy_profile(results: Dict[str, Any]):
    dates = pd.date_range(start='2023-01-01', periods=8760, freq='h')
    df = pd.DataFrame({
#        'Farm Base': results['hourly_consumption']['farm_base'],
        'Farm Irrigation': results['hourly_consumption']['farm_irrigation'],
        'Data Center': results['hourly_consumption']['data_center'],
        'Extra': results['hourly_production'] - results['hourly_consumption']['total']
    }, index=dates)
    
    df['Extra_Positive'] = df['Extra'].clip(lower=0)
    df['Extra_Negative'] = df['Extra'].clip(upper=0)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
    
    # Yearly plot
    daily_df = df.resample('D').sum()
#    daily_df[['Farm Base', 'Farm Irrigation', 'Data Center', 'Extra_Positive']].plot(ax=ax1, kind='area', stacked=True)
    daily_df[['Farm Irrigation', 'Data Center', 'Extra_Positive']].plot(ax=ax1, kind='area', stacked=True)
    daily_df['Extra_Negative'].plot(ax=ax1, color='red', label='Energy Deficit')
    ax1.set_title('Daily Energy Profile (Yearly)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Energy (kWh)')
    ax1.legend()

    # Monthly plot (using Aug-Sept as an example)
    july_data = df['2023-08-15':'2023-09-15']
#    july_data[['Farm Base', 'Farm Irrigation', 'Data Center', 'Extra_Positive']].plot(ax=ax2, kind='area', stacked=True)
    july_data[['Farm Irrigation', 'Data Center', 'Extra_Positive']].plot(ax=ax2, kind='area', stacked=True)
    july_data['Extra_Negative'].plot(ax=ax2, color='red', label='Energy Deficit')
    ax2.set_title('Hourly Energy Profile (July)')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Energy (kWh)')
    ax2.legend()
    ax2.xaxis.set_major_formatter(DateFormatter('%d-%b'))

    plt.tight_layout()
    plt.show()

def plot_energy_data(data: Dict[str, np.ndarray], title: str, y_label: str, 
                     plot_type: str = 'line', stacked: bool = False):
    dates = pd.date_range(start='2023-01-01', periods=8760, freq='h')
    df = pd.DataFrame(data, index=dates)
    
    if 'Extra' in df.columns:
        df['Extra_Positive'] = df['Extra'].clip(lower=0)
        df['Extra_Negative'] = df['Extra'].clip(upper=0)
        df = df.drop(columns=['Extra'])
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
    
    # Yearly plot
    daily_df = df.resample('D').sum()
    if plot_type == 'area' and stacked:
        daily_df[['Farm Irrigation', 'Data Center', 'Extra_Positive']].plot(ax=ax1, kind='area', stacked=True)
        if 'Extra_Negative' in daily_df.columns:
            daily_df['Extra_Negative'].plot(ax=ax1, color='red', label='Energy Deficit')
    else:
        daily_df.plot(ax=ax1)
    ax1.set_title(f'Daily {title} (Yearly)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel(y_label)
    ax1.legend()

    # Monthly plot (using Aug-Sept as an example)
    monthly_data = df['2023-08-15':'2023-09-15']
    if plot_type == 'area' and stacked:
        monthly_data[['Farm Irrigation', 'Data Center', 'Extra_Positive']].plot(ax=ax2, kind='area', stacked=True)
        if 'Extra_Negative' in monthly_data.columns:
            monthly_data['Extra_Negative'].plot(ax=ax2, color='red', label='Energy Deficit')
    else:
        monthly_data.plot(ax=ax2)
    ax2.set_title(f'Hourly {title} (August-September)')
    ax2.set_xlabel('Date')
    ax2.set_ylabel(y_label)
    ax2.legend()
    ax2.xaxis.set_major_formatter(DateFormatter('%d-%b'))

    plt.tight_layout()
    plt.show()

def plot_battery_profile(results: Dict[str, Any]):
    dates = pd.date_range(start='2023-01-01', periods=8760, freq='h')
    df = pd.DataFrame({
        'Battery Charge': results['battery_charge'],
        'Energy Deficit': results['energy_deficit']
    }, index=dates)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
    
    # Yearly plot
    df.resample('D').mean().plot(ax=ax1)
    ax1.set_title('Daily Average Battery Charge and Energy Deficit (Yearly)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Energy (kWh)')
    ax1.legend()

    # Monthly plot (using Aug-Sept as an example)
    july_data = df['2023-08-15':'2023-09-15']
    july_data.plot(ax=ax2)
    ax2.set_title('Hourly Battery Charge and Energy Deficit (July)')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Energy (kWh)')
    ax2.legend()
    ax2.xaxis.set_major_formatter(DateFormatter('%d-%b'))

    plt.tight_layout()
    plt.show()

def plot_energy_allocation(results: List[Dict[str, float]]):
    df = pd.DataFrame(results)
    df['datetime'] = pd.date_range(start='2023-01-01', periods=len(df), freq='H')
    df.set_index('datetime', inplace=True)

    fig, ax = plt.subplots(figsize=(15, 8))
    ax.stackplot(df.index, df['irrigation'], df['servers'], df['gpu'], 
                 labels=['Irrigation', 'Servers', 'GPU'])
    ax.plot(df.index, df['production'], color='r', label='Production')
    ax.set_title('Energy Allocation Over Time')
    ax.set_xlabel('Date')
    ax.set_ylabel('Energy (kWh)')
    ax.legend(loc='upper left')
    plt.tight_layout()
    plt.show()

def calculate_economics(results: List[Dict[str, float]], electricity_price: float, gpu_revenue_rate: float) -> Dict[str, float]:
    df = pd.DataFrame(results)
    total_production = df['production'].sum()
    total_consumption = df['total_consumption'].sum()
    gpu_revenue = (df['gpu'] * gpu_revenue_rate).sum()
    electricity_savings = total_production * electricity_price
    return {
        'total_production': total_production,
        'total_consumption': total_consumption,
        'gpu_revenue': gpu_revenue,
        'electricity_savings': electricity_savings,
        'net_benefit': gpu_revenue + electricity_savings
    }
    
def generate_report_off_grid(results: Dict[str, Any], solar_park: SolarParkSimulator, battery: BatteryStorage):
    print(f"Off-Grid Solar Park Simulation Report for {solar_park.location}")
    print("=" * 70)
    print(f"Total Capacity: {solar_park.total_capacity:.2f} kWp")
    print(f"Inverter Capacity: {solar_park.inverter_capacity:.2f} kWn")
    print(f"Battery Capacity: {battery.capacity:.2f} kWh")
    print(f"Performance Ratio: {solar_park.performance_ratio:.2f}")
    print(f"Specific Yield: {results['specific_yield']:.2f} kWh/kWp")
    print(f"\nTotal Annual Energy Production: {np.sum(results['hourly_production']):.2f} kWh")
    print(f"Total Annual Energy Consumption: {np.sum(results['hourly_consumption']['total']):.2f} kWh")
    print(f"Total Energy Deficit: {np.sum(results['energy_deficit']):.2f} kWh")
    
    utilization_ratio = np.sum(results['hourly_consumption']['total']) / np.sum(results['hourly_production'])
    print(f"\nEnergy Utilization Ratio: {utilization_ratio:.2%}")
    
    min_battery_level = np.min(results['battery_charge'])
    print(f"Minimum Battery Level: {min_battery_level:.2f} kWh ({min_battery_level/battery.capacity:.2%} of capacity)")

def run_annual_simulation(solar_park: SolarParkSimulator, energy_profile: EnergyProfile, battery: BatteryStorage, ems: EnergyManagementSystem) -> List[Dict[str, float]]:
    results = []
    for day in range(365):
        for hour in range(24):
            month = next(m for m, days in enumerate(np.cumsum(energy_profile.days_in_month)) if day < days)
            weather = solar_park.weather_simulator.simulate_hour(day + 1, hour)
            production = solar_park.calculate_hourly_energy(weather)
            
            allocation = ems.allocate_energy(production, month, hour, weather)
            
            energy_deficit = max(0, allocation['total_consumption'] - production - allocation['battery_change'])
            
            step_data = {
                **weather, 
                **allocation, 
                'production': production,
                'battery_charge': battery.charge,
                'energy_deficit': energy_deficit,
                'datetime': datetime(2023, 1, 1) + timedelta(days=day, hours=hour)
            }
            
            validate_simulation_step(step_data)
            results.append(step_data)
            
            # Update energy profile debug data
            energy_profile.hourly_consumption(month, hour, weather, production + battery.charge)
    
    return results

def validate_simulation_step(step_data: Dict[str, float]):
    if step_data['production'] < 0:
        raise ValueError(f"Negative energy production: {step_data['production']}")
    if step_data['total_consumption'] < 0:
        raise ValueError(f"Negative energy consumption: {step_data['total_consumption']}")
    if step_data['battery_charge'] < 0:
        raise ValueError(f"Negative battery charge: {step_data['battery_charge']}")
    
    if step_data['total_consumption'] == 0:
        logging.warning(f"Zero consumption at {step_data['datetime']}")
    
    if step_data['production'] == 0 and step_data['sun_intensity'] > 0:
        logging.warning(f"Zero production with non-zero sun intensity at {step_data['datetime']}")

def generate_comprehensive_daily_report(day: int, weather_sim: WeatherSimulator, solar_park: SolarParkSimulator, 
                                        energy_profile: EnergyProfile, battery: BatteryStorage, 
                                        ems: EnergyManagementSystem) -> str:
    weather_data = weather_sim.get_daily_data(day)
    energy_production = solar_park.get_daily_production(weather_data)
    energy_consumption = energy_profile.get_daily_consumption(day, weather_data, energy_production)
    battery_data = battery.get_daily_data()
    energy_allocation = ems.get_daily_allocation(day, weather_data)

    report = f"Daily Report for Day {day + 1}\n"
    report += "=" * 40 + "\n\n"

    report += "Weather Data:\n"
    for key in weather_data:
        report += f"  {key}: {weather_data[key]}\n"
    report += "\n"

    report += "Energy Production (kWh):\n"
    report += f"  {energy_production}\n\n"

    report += "Energy Consumption (kWh):\n"
    for key in energy_consumption:
        report += f"  {key}: {energy_consumption[key]}\n"
    report += "\n"

    report += "Battery Data:\n"
    for key, value in battery_data.items():
        report += f"  {key}: {value}\n"
    report += "\n"

    report += "Energy Allocation:\n"
    for hour, allocation in enumerate(energy_allocation):
        report += f"  Hour {hour}:\n"
        for key, value in allocation.items():
            report += f"    {key}: {value}\n"
    report += "\n"

    # Calculate energy available for 24/7 supply and surplus
    total_production = sum(energy_production)
    total_consumption = sum(energy_consumption['total'])
    energy_surplus = [max(0, energy_production[i] - energy_consumption['total'][i]) for i in range(24)]
    
    report += "Energy Analysis:\n"
    report += f"  Total Production: {total_production:.2f} kWh\n"
    report += f"  Total Consumption: {total_consumption:.2f} kWh\n"
    report += f"  Energy Available for 24/7 Supply: {min(energy_production):.2f} kWh/hour\n"
    report += f"  Total Energy Surplus: {sum(energy_surplus):.2f} kWh\n"
    report += "  Hourly Energy Surplus:\n"
    for hour, surplus in enumerate(energy_surplus):
        report += f"    Hour {hour}: {surplus:.2f} kWh\n"

    return report
    
def main():
    # Solar park specifications
    location = "Beja, Portugal"
    total_capacity = 947.52  # kWp
    inverter_capacity = 800  # kWn
    performance_ratio = 0.75
    battery_capacity = 500  # kWh

    # Create simulators
    solar_park = SolarParkSimulator(location, total_capacity, inverter_capacity, performance_ratio)
    energy_profile = EnergyProfile()
    battery = BatteryStorage(battery_capacity)
    
    # Create energy management system
    ems = EnergyManagementSystem(solar_park, energy_profile, battery)
    
    # Run simulations
    results = run_annual_simulation(solar_park, energy_profile, battery, ems)
    
    # Convert results list to more usable format
    df_results = pd.DataFrame(results)
    
    # Generate and save debug report
    debug_report = energy_profile.generate_debug_report()
    with open('energy_profile_debug_report.txt', 'w') as f:
        f.write(debug_report)

    # Calculate totals and averages
    total_production = df_results['production'].sum()
    total_consumption = df_results['total_consumption'].sum()
    average_battery_charge = df_results['battery_charge'].mean()
    total_energy_deficit = df_results['energy_deficit'].sum() if 'energy_deficit' in df_results else 0

    results_summary = {
        'hourly_production': df_results['production'].values,
        'hourly_consumption': {
            'total': df_results['total_consumption'].values,
            'farm_irrigation': df_results['irrigation'].values,
            'data_center': df_results['servers'].values + df_results['gpu'].values
        },
        'battery_charge': df_results['battery_charge'].values,
        'energy_deficit': df_results['energy_deficit'].values if 'energy_deficit' in df_results else np.zeros(8760),
        'total_annual_production': total_production,
        'total_annual_consumption': total_consumption,
        'average_battery_charge': average_battery_charge,
        'total_energy_deficit': total_energy_deficit,
        'specific_yield': total_production / total_capacity
    }

    # Generate comprehensive daily reports
    full_report = ""
    for day in range(365):
        daily_report = generate_comprehensive_daily_report(day, solar_park.weather_simulator, solar_park, energy_profile, battery, ems)
        full_report += daily_report + "\n" + "=" * 80 + "\n\n"

    # Save the full report
    with open('comprehensive_energy_report.txt', 'w') as f:
        f.write(full_report)
    # Generate and print report
    generate_report_off_grid(results_summary, solar_park, battery)

    # Plot energy production, consumption, and battery usage
    plot_energy_data({
        'Production': results_summary['hourly_production'],
        'Consumption': results_summary['hourly_consumption']['total']
    }, 'Energy Production and Consumption', 'Energy (kWh)')
    
    plot_energy_data({
        'Farm Irrigation': results_summary['hourly_consumption']['farm_irrigation'],
        'Data Center': results_summary['hourly_consumption']['data_center'],
        'Extra': results_summary['hourly_production'] - results_summary['hourly_consumption']['total']
    }, 'Energy Profile', 'Energy (kWh)', plot_type='area', stacked=True)
    
    plot_battery_profile(results_summary)

if __name__ == "__main__":
    main()
# Calculation, Sent over Telegram version
# Key notes:
# 1) WeatherSimulator doesn't have per hourly simulation (minimal is per day)
# 2) WeatherSimulator daily simulation has dependency from previous day
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any
from config import load_config

class WeatherSimulator:
    def __init__(self, location: str):
        self.location = location
        self.monthly_data = {
            'sun_hours': [7.18, 9.18, 10.07, 11.52, 13.34, 13.89, 14.0, 13.56, 11.19, 8.85, 7.38, 7.33],
            'precipitation': [24.16, 27.53, 36.22, 41.97, 26.91, 6.36, 1.76, 2.97, 16.72, 40.79, 41.49, 25.15],
            'temp': [10.45, 11.05, 13.47, 16.43, 21.09, 24.92, 27.79, 28.1, 25.4, 20.63, 14.55, 11.62],
            'wind_speed': [22, 22, 22, 22, 22, 22, 25, 22, 22, 22, 22, 22],
            'humidity': [80.81, 78.19, 77.66, 73.91, 60.69, 52.84, 48.86, 47.07, 51.93, 60.7, 73.48, 76.96],
        }
        self.days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        self.wind_directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

    def simulate_day(self, day_of_year: int, prev_day: Dict[str, Any] = None) -> Dict[str, Any]:
        month = next(m for m, days in enumerate(self._cumulative_days()) if day_of_year <= days) - 1
        
        # Interpolate daily values from monthly data
        sun_hours = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['sun_hours'])
        temp = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['temp'])
        wind_speed = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['wind_speed'])
        humidity = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['humidity'])

        # Determine wind direction
        wind_direction = np.random.choice(self.wind_directions)
        
        # Calculate cloud cover
        if prev_day:
            base_cloud_cover = prev_day['cloud_cover']
            wind_effect = (wind_speed - 22) * 0.02
            cloud_cover = max(0, min(1, base_cloud_cover - wind_effect + np.random.normal(0, 0.1)))
        else:
            cloud_cover = np.random.beta(2, 5)

        # Adjust sun hours and temperature based on cloud cover
        sun_hours *= (1 - cloud_cover * 0.5)
        temp += (1 - cloud_cover) * 2

        return {
            'sun_hours': sun_hours,
            'temperature': temp,
            'wind_speed': wind_speed,
            'wind_direction': wind_direction,
            'cloud_cover': cloud_cover,
            'humidity': humidity
        }

    def simulate_year(self) -> List[Dict[str, Any]]:
        daily_weather = []
        prev_day = None
        for day in range(365):
            day_weather = self.simulate_day(day + 1, prev_day)
            daily_weather.append(day_weather)
            prev_day = day_weather
        return daily_weather

    def _cumulative_days(self) -> List[int]:
        return [sum(self.days_in_month[:i+1]) for i in range(12)]

    def _mid_month_days(self) -> List[int]:
        cum_days = [0] + self._cumulative_days()
        return [(cum_days[i] + cum_days[i+1]) // 2 for i in range(12)]

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

    def calculate_daily_energy(self, weather: Dict[str, Any]) -> float:
        base_energy = self.total_capacity * weather['sun_hours'] * self.performance_ratio

        # Apply adjustments
        temp_adjustment = 1 + self.temp_coefficient * (weather['temperature'] - 25)
        wind_adjustment = 1 + 0.002 * (weather['wind_speed'] - 22)
        cloud_adjustment = 1 - (weather['cloud_cover'] * 0.5)

        energy_produced = base_energy * temp_adjustment * wind_adjustment * cloud_adjustment

        # Cap at inverter capacity
        return min(energy_produced, self.inverter_capacity * 24)

    def simulate_annual_production(self) -> Dict[str, np.ndarray]:
        weather_data = self.weather_simulator.simulate_year()
        daily_production = np.array([self.calculate_daily_energy(day) for day in weather_data])

        return {
            'energy_production': daily_production,
            'weather_data': weather_data
        }

    def run_simulation(self) -> Dict[str, Any]:
        simulation_data = self.simulate_annual_production()
        daily_production = simulation_data['energy_production']
        total_annual_production = np.sum(daily_production)
        specific_yield = total_annual_production / self.total_capacity

        monthly_production = np.array([np.sum(daily_production[sum(self.weather_simulator.days_in_month[:i]):sum(self.weather_simulator.days_in_month[:i+1])]) for i in range(12)])
        peak_production_day = np.argmax(daily_production) + 1
        lowest_production_day = np.argmin(daily_production) + 1

        return {
            "daily_production": daily_production,
            "total_annual_production": total_annual_production,
            "specific_yield": specific_yield,
            "monthly_production": monthly_production,
            "peak_production_day": peak_production_day,
            "lowest_production_day": lowest_production_day,
            "weather_data": simulation_data['weather_data']
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

class EnergyProfile:
    def __init__(self, config):
        self.pumps_power = config.pumps_power
        self.programmer_power = config.programmer_power
        self.dosing_pump_power = config.dosing_pump_power
        self.irrigation_months = np.array(config.irrigation_months)
        self.pumps_hours = 8
        self.programmer_hours = 24
        self.dosing_pump_hours = 8

    def daily_consumption(self, month: int, is_cloudy: bool) -> float:
        if month in self.irrigation_months and not is_cloudy:
            pumps_energy = self.pumps_power * self.pumps_hours
            programmer_energy = self.programmer_power * self.programmer_hours
            dosing_pump_energy = self.dosing_pump_power * self.dosing_pump_hours
            return pumps_energy + programmer_energy + dosing_pump_energy
        else:
            return self.programmer_power * self.programmer_hours  # Only programmer runs year-round

    def annual_consumption(self, weather_data: List[Dict[str, Any]]) -> np.ndarray:
        daily_consumption = []
        for day in range(365):
            month = next(m for m, days in enumerate(np.cumsum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])) if day < days)
            is_cloudy = weather_data[day]['cloud_cover'] > 0.5  # Assume cloudy if cloud cover > 50%
            daily_consumption.append(self.daily_consumption(month, is_cloudy))
        return np.array(daily_consumption)

class BatteryStorage:
    def __init__(self, capacity: float, initial_charge: float = None, efficiency: float = 0.9):
        self.capacity = capacity
        self.charge = initial_charge if initial_charge is not None else capacity * 0.5
        self.efficiency = efficiency

    def charge_battery(self, energy: float) -> float:
        energy_to_store = energy * np.sqrt(self.efficiency)
        actual_stored = min(energy_to_store, self.capacity - self.charge)
        self.charge += actual_stored
        return actual_stored / np.sqrt(self.efficiency)

    def discharge_battery(self, energy_needed: float) -> float:
        energy_to_discharge = min(energy_needed / np.sqrt(self.efficiency), self.charge)
        self.charge -= energy_to_discharge
        return energy_to_discharge * np.sqrt(self.efficiency)

def simulate_off_grid(daily_production: np.ndarray, daily_consumption: np.ndarray, battery: BatteryStorage, extra_load: float) -> Dict[str, np.ndarray]:
    total_consumption = daily_consumption + extra_load
    battery_charge = np.zeros(len(daily_production))
    energy_deficit = np.zeros(len(daily_production))
    
    for day in range(len(daily_production)):
        net_energy = daily_production[day] - total_consumption[day]
        
        if net_energy > 0:
            # Excess energy: charge battery
            battery.charge_battery(net_energy)
        else:
            # Energy deficit: discharge battery
            energy_from_battery = battery.discharge_battery(-net_energy)
            if energy_from_battery < -net_energy:
                energy_deficit[day] = -net_energy - energy_from_battery
        
        battery_charge[day] = battery.charge

    return {
        'battery_charge': battery_charge,
        'energy_deficit': energy_deficit,
        'total_consumption': total_consumption
    }

def find_max_continuous_load(daily_production: np.ndarray, daily_consumption: np.ndarray, battery: BatteryStorage) -> float:
    low = 0
    high = np.mean(daily_production) - np.mean(daily_consumption)
    
    while high - low > 0.1:  # 0.1 kWh precision
        mid = (low + high) / 2
        results = simulate_off_grid(daily_production, daily_consumption, BatteryStorage(battery.capacity), mid)
        
        if np.sum(results['energy_deficit']) > 0:
            high = mid
        else:
            low = mid
    
    return low

def plot_energy_balance_off_grid(results: Dict[str, Any]):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 16))

    # Daily energy flow
    ax1.plot(results['daily_production'], label='Production', color='green')
    ax1.plot(results['total_consumption'], label='Total Consumption', color='red')
    ax1.set_title('Daily Energy Production and Consumption')
    ax1.set_xlabel('Day of Year')
    ax1.set_ylabel('Energy (kWh)')
    ax1.legend()

    # Battery charge level
    ax2.plot(results['battery_charge'], label='Battery Charge', color='purple')
    ax2.set_title('Daily Battery Charge Level')
    ax2.set_xlabel('Day of Year')
    ax2.set_ylabel('Energy (kWh)')
    ax2.set_ylim(0, results['battery_charge'].max() * 1.1)
    ax2.legend()

    plt.tight_layout()
    plt.show()

def generate_report_off_grid(results: Dict[str, Any], solar_park: SolarParkSimulator, battery: BatteryStorage, max_continuous_load: float):
    print(f"Off-Grid Solar Park Simulation Report for {solar_park.location}")
    print("=" * 70)
    print(f"Total Capacity: {solar_park.total_capacity:.2f} kWp")
    print(f"Inverter Capacity: {solar_park.inverter_capacity:.2f} kWn")
    print(f"Battery Capacity: {battery.capacity:.2f} kWh")
    print(f"Performance Ratio: {solar_park.performance_ratio:.2f}")
    print(f"\nTotal Annual Energy Production: {results['total_annual_production']:.2f} kWh")
    print(f"Specific Yield: {results['specific_yield']:.2f} kWh/kWp")
    print(f"Total Annual Base Consumption: {results['total_annual_consumption']:.2f} kWh")
    print(f"Maximum Continuous Extra Load: {max_continuous_load:.2f} kW")
    print(f"Potential Annual Extra Consumption: {max_continuous_load * 24 * 365:.2f} kWh")
    
    total_consumption = results['total_annual_consumption'] + (max_continuous_load * 24 * 365)
    print(f"Total Potential Annual Consumption: {total_consumption:.2f} kWh")
    
    utilization_ratio = total_consumption / results['total_annual_production']
    print(f"\nEnergy Utilization Ratio: {utilization_ratio:.2%}")
    
    min_battery_level = np.min(results['battery_charge'])
    print(f"Minimum Battery Level: {min_battery_level:.2f} kWh ({min_battery_level/battery.capacity:.2%} of capacity)")

def main():
    # Create simulators
    config = load_config()
    solar_park = SolarParkSimulator(
        location=config.weather.location,
        total_capacity=config.solar_park.total_capacity,
        inverter_capacity=config.solar_park.inverter_capacity,
        performance_ratio=config.solar_park.performance_ratio
    )
    energy_profile = EnergyProfile(config.energy_profile)
    battery = BatteryStorage(
        capacity=config.battery.capacity,
        initial_charge=config.battery.initial_charge,
        efficiency=config.battery.efficiency
    )
    
    # Run simulations
    simulation_results = solar_park.run_simulation()
    daily_consumption = energy_profile.annual_consumption(simulation_results['weather_data'])
    
    max_continuous_load = find_max_continuous_load(simulation_results['daily_production'], daily_consumption, battery)
    
    results = simulate_off_grid(simulation_results['daily_production'], daily_consumption, battery, max_continuous_load)
    results.update({
        'daily_production': simulation_results['daily_production'],
        'total_annual_production': np.sum(simulation_results['daily_production']),
        'total_annual_consumption': np.sum(daily_consumption),
        'specific_yield': simulation_results['specific_yield']

    })

    # Generate and print report
    generate_report_off_grid(results, solar_park, battery, max_continuous_load)

    # Plot energy production, consumption, and battery usage
    plot_energy_balance_off_grid(results)

if __name__ == "__main__":
    main()
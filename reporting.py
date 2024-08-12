import numpy as np
from typing import Dict, Any
from solar_park_simulator import SolarParkSimulator
from energy_profile import EnergyProfile
from battery_storage import BatteryStorage
from energy_management_system import EnergyManagementSystem
from weather_simulator import WeatherSimulator

def generate_report_off_grid(results: Dict[str, Any], solar_park: SolarParkSimulator, battery: BatteryStorage):
    print(f"Off-Grid Solar Park Simulation Report for {solar_park.weather_simulator.location}")
    print("=" * 70)
    print(f"Total Capacity: {solar_park.total_capacity:.2f} kWp")
    print(f"Inverter Capacity: {solar_park.inverter_capacity:.2f} kWn")
    print(f"Battery Capacity: {battery.capacity:.2f} kWh")
    print(f"Performance Ratio: {solar_park.performance_ratio:.2f}")
    print(f"Specific Yield: {results['specific_yield']:.2f} kWh/kWp")
    print(f"\nTotal Annual Energy Production: {results['total_annual_production']:.2f} kWh")
    print(f"Total Annual Energy Consumption: {results['total_annual_consumption']:.2f} kWh")
    print(f"Total Energy Deficit: {results['total_energy_deficit']:.2f} kWh")
    
    utilization_ratio = results['total_annual_consumption'] / results['total_annual_production']
    print(f"\nEnergy Utilization Ratio: {utilization_ratio:.2%}")
    
    min_battery_level = np.min(results['battery_charge'])
    print(f"Minimum Battery Level: {min_battery_level:.2f} kWh ({min_battery_level/battery.capacity:.2%} of capacity)")

    print("\nAnnual Revenue:")
    print(f"  Staking: €{results['annual_revenue']['staking']:.2f}")
    print(f"  GPU Rental: €{results['annual_revenue']['gpu_rental']:.2f}")
    print(f"  Total: €{results['annual_revenue']['total']:.2f}")
    print(f"  Profitability: {results['annual_revenue']['ROI']:.2f}%")

    print("\nROI Analysis (7-year period):")
    print(f"  Total Revenue: €{results['roi_analysis']['total_revenue_7years']:.2f}")
    print(f"  CapEx: €{results['roi_analysis']['capex']:.2f}")    
    print(f"  Profit: ${results['roi_analysis']['profit_7years']:.2f}")
    print(f"  ROI: {results['roi_analysis']['roi_7years']:.2f}%")
    print(f"  Payback Period: {results['roi_analysis']['payback_period']:.2f} years")

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
import numpy as np
from typing import Dict, Any
import os
from datetime import datetime
from solar_park_simulator import SolarParkSimulator
from energy_profile import EnergyProfile
from battery_storage import BatteryStorage
from energy_management_system import EnergyManagementSystem
from weather_simulator import WeatherSimulator
from config import SolarParkConfig

def generate_report_off_grid(results: Dict[str, Any], solar_park, battery, energy_profile, config):
    report = f"Off-Grid Solar Park Simulation Report for {solar_park.weather_simulator.location}\n"
    report += "=" * 70 + "\n\n"
    report += f"Simulation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    report += f"Total Capacity: {solar_park.total_capacity:.2f} kWp\n"
    report += f"Inverter Capacity: {solar_park.inverter_capacity:.2f} kWn\n"
    report += f"Battery Capacity: {battery.capacity:.2f} kWh\n"
    report += f"Performance Ratio: {solar_park.performance_ratio:.2f}\n"
    report += f"Specific Yield: {results['specific_yield']:.2f} kWh/kWp\n"
    report += f"\nTotal Annual Energy Production: {results['total_annual_production']:.2f} kWh\n"
    report += f"Total Annual Energy Consumption: {results['total_annual_consumption']:.2f} kWh\n"
    report += f"Total Energy Deficit: {results['total_energy_deficit']:.2f} kWh\n"
    
    utilization_ratio = results['total_annual_consumption'] / results['total_annual_production']
    report += f"\nEnergy Utilization Ratio: {utilization_ratio:.2%}\n"
    
    min_battery_level = np.min(results['battery_charge'])
    report += f"Minimum Battery Level: {min_battery_level:.2f} kWh ({min_battery_level/battery.capacity:.2%} of capacity)\n"

#    report += "\nMonthly Energy Production (kWh):\n"
#    for month, production in enumerate(solar_park['monthly_production'], 1):
#        report += f"  Month {month}: {production:.2f}\n"

    report += "\nEnergy Consumption Breakdown:\n"
    report += f"  Irrigation: {results['hourly_consumption']['farm_irrigation']:.2f} kWh\n"
    report += f"  Servers: {results['hourly_consumption']['servers']:.2f} kWh\n"
    report += f"  GPU: {results['hourly_consumption']['gpu']:.2f} kWh\n"

    report += "\nAnnual Revenue:\n"
    report += f"  Staking: €{results['annual_revenue']['staking']:.2f}\n"
    report += f"  GPU Rental: €{results['annual_revenue']['gpu_rental']:.2f}\n"
    report += f"  Total: €{results['annual_revenue']['total']:.2f}\n"
    report += f"  Profitability: {results['annual_revenue']['ROI']:.2f}%\n"

    report += "\nROI Analysis (7-year period):\n"
    report += f"  Total Revenue: €{results['roi_analysis']['total_revenue_7years']:.2f}\n"
    report += f"  CapEx: €{results['roi_analysis']['capex']:.2f}\n"
    report += f"  Profit: €{results['roi_analysis']['profit_7years']:.2f}\n"
    report += f"  ROI: {results['roi_analysis']['roi_7years']:.2f}%\n"
    report += f"  Payback Period: {results['roi_analysis']['payback_period']:.2f} years\n"

    report += "\nEnvironmental Impact:\n"
    co2_avoided = results['total_annual_production'] * 0.45  # Assuming 0.45 kg CO2 per kWh
    report += f"  CO2 Emissions Avoided: {co2_avoided:.2f} kg\n"

    report += "\nSystem Efficiency:\n"
    report += f"  Panel Efficiency: {solar_park.panel_efficiency:.2%}\n"
    report += f"  Inverter Efficiency: {config.inverter_efficiency:.2%}\n"
    report += f"  Battery Efficiency: {battery.efficiency:.2%}\n"

    # Save the report to a file
    reports_dir = 'reports'
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    report_file = os.path.join(reports_dir, f'simulation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    with open(report_file, 'w') as f:
        f.write(report)

    print(report)
    print(f"\nReport saved to: {report_file}")

    return report

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
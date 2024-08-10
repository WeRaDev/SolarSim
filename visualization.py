import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import os
from typing import Dict, Any
from solar_park_simulator import SolarParkSimulator
from battery_storage import BatteryStorage
import numpy as np

def ensure_charts_directory():
    if not os.path.exists('charts'):
        os.makedirs('charts')

def load_data():
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'simulation_data.csv')
    df = pd.read_csv(data_path, parse_dates=['datetime'])
    df.set_index('datetime', inplace=True)
    return df

def plot_chart(df, x, y, title, xlabel, ylabel, scale='year'):
    plt.figure(figsize=(12, 6))
    if isinstance(y, list):
        for col in y:
            plt.plot(df.index, df[col], label=col)
        plt.legend()
    else:
        plt.plot(df.index, df[y])
    
    plt.title(f"{title} ({scale.capitalize()} Scale)")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    
    if scale == 'year':
        plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    elif scale == 'week':
        plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    elif scale == 'day':
        plt.gca().xaxis.set_major_formatter(DateFormatter('%H:%M'))
    
    plt.tight_layout()
    ensure_charts_directory()
    plt.savefig(f"charts/{title.lower().replace(' ', '_')}_{scale}.png")
    plt.close()

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

def generate_charts():
    ensure_charts_directory()
    df = load_data()
    
    # Calculate available energy for the entire dataset
    df['available_energy'] = df['production'] + df['battery_charge']
    
    # Define time ranges
    year_range = df.index
    summer_week = df.loc['2023-08-15':'2023-08-22'].copy()
    winter_week = df.loc['2023-03-15':'2023-03-22'].copy()
    summer_day = df.loc['2023-08-23'].copy()
    winter_day = df.loc['2023-03-23'].copy()
    
    # Calculate available energy for each subset
    for subset in [summer_week, winter_week, summer_day, winter_day]:
        subset['available_energy'] = subset['production'] + subset['battery_charge']
    
    # 1. Energy production vs weather conditions
    weather_conditions = ['sun_intensity', 'temperature', 'humidity', 'cloud_cover', 'wind_speed']
    for condition in weather_conditions:
        plot_chart(df, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'year')
        plot_chart(summer_week, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'week')
        plot_chart(winter_week, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'week')
        plot_chart(summer_day, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'day')
        plot_chart(winter_day, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'day')
    
    # 2. Energy production versus consumption
    plot_chart(df, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'year')
    plot_chart(summer_week, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'week')
    plot_chart(winter_week, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'week')
    plot_chart(summer_day, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'day')
    plot_chart(winter_day, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'day')
    
    # 3. Energy profile vs allocation
    energy_components = ['irrigation', 'servers', 'gpu']
    plot_chart(df, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'year')
    plot_chart(summer_week, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'week')
    plot_chart(winter_week, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'week')
    plot_chart(summer_day, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'day')
    plot_chart(winter_day, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'day')
    
    # 4. Available energy vs energy profile
    plot_chart(df, 'datetime', ['available_energy', 'total_consumption'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'year')
    plot_chart(summer_week, 'datetime', ['available_energy', 'total_consumption'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'week')
    plot_chart(winter_week, 'datetime', ['available_energy', 'total_consumption'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'week')
    plot_chart(summer_day, 'datetime', ['available_energy', 'total_consumption'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'day')
    plot_chart(winter_day, 'datetime', ['available_energy', 'total_consumption'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'day')
    
    # 5. Profit generated versus energy produced
    # Note: We need to calculate profit. This is a simplified version.
    df['profit'] = (df['servers'] + df['gpu']) * 0.1 - df['energy_deficit'] * 0.15  # Assuming some profit margins
    summer_week['profit'] = (summer_week['servers'] + summer_week['gpu']) * 0.1 - summer_week['energy_deficit'] * 0.15
    winter_week['profit'] = (winter_week['servers'] + winter_week['gpu']) * 0.1 - winter_week['energy_deficit'] * 0.15
    summer_day['profit'] = (summer_day['servers'] + summer_day['gpu']) * 0.1 - summer_day['energy_deficit'] * 0.15
    winter_day['profit'] = (winter_day['servers'] + winter_day['gpu']) * 0.1 - winter_day['energy_deficit'] * 0.15
    
    plot_chart(df, 'production', 'profit', 'Profit Generated vs Energy Produced', 'Energy Produced (kWh)', 'Profit ($)', 'year')
    plot_chart(summer_week, 'production', 'profit', 'Profit Generated vs Energy Produced', 'Energy Produced (kWh)', 'Profit ($)', 'week')
    plot_chart(winter_week, 'production', 'profit', 'Profit Generated vs Energy Produced', 'Energy Produced (kWh)', 'Profit ($)', 'week')
    plot_chart(summer_day, 'production', 'profit', 'Profit Generated vs Energy Produced', 'Energy Produced (kWh)', 'Profit ($)', 'day')
    plot_chart(winter_day, 'production', 'profit', 'Profit Generated vs Energy Produced', 'Energy Produced (kWh)', 'Profit ($)', 'day')

if __name__ == "__main__":
    generate_charts()
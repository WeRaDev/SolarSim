import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.dates import DateFormatter
import os
from typing import Dict, Any, List, Union
import numpy as np
from config import load_config

# Add seaborn for improved plot aesthetics
sns.set_style("whitegrid")

def ensure_charts_directory():
    if not os.path.exists('charts'):
        os.makedirs('charts')

def load_data():
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'simulation_data.csv')
    df = pd.read_csv(data_path, parse_dates=['datetime'])
    df.set_index('datetime', inplace=True)
    return df

# Updated plot_chart function with more flexibility and improved aesthetics
def plot_chart(df: pd.DataFrame, x: str, y: Union[str, List[str]], title: str, xlabel: str, ylabel: str, scale: str = 'year', kind: str = 'line'):
    plt.figure(figsize=(12, 6))
    
    if kind == 'line':
        if isinstance(y, list):
            for col in y:
                sns.lineplot(data=df, x=x, y=col, label=col)
        else:
            sns.lineplot(data=df, x=x, y=y, label=y)
    elif kind == 'scatter':
        if isinstance(y, list):
            for col in y:
                sns.scatterplot(data=df, x=x, y=col, label=col, alpha=0.6)
        else:
            sns.scatterplot(data=df, x=x, y=y, label=y, alpha=0.6)
    elif kind == 'area':
        if isinstance(y, list):
            df[y].plot.area(stacked=True, alpha=0.7)
        else:
            df[y].plot.area(alpha=0.7, label=y)
    
    plt.title(f"{title} ({scale.capitalize()} Scale)", fontsize=16)
    plt.xlabel(xlabel, fontsize=12)
    plt.ylabel(ylabel, fontsize=12)
    
    if scale == 'year':
        plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m'))
    elif scale == 'week':
        plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
    elif scale == 'day':
        plt.gca().xaxis.set_major_formatter(DateFormatter('%H:%M'))
    
    plt.xticks(rotation=45)
    
    # Only add legend if there are labeled artists
    if plt.gca().get_legend_handles_labels()[0]:
        plt.legend(fontsize=10)
    
    plt.tight_layout()
    
    ensure_charts_directory()
    filename = f"charts/{title.lower().replace(' ', '_')}_{scale}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved chart: {filename}")

# Remove unused functions
# Removed plot_energy_data and plot_battery_profile as they're not used in generate_charts

def generate_charts():
    config = load_config()
    year = config.year
    
    ensure_charts_directory()
    df = load_data()
    
    # Calculate available energy for the entire dataset
    df['available_energy'] = df['production'] + df['battery_charge']
    
    # Define time ranges
    year_range = df.index
    summer_week = df.loc[f'{year}-08-15':f'{year}-08-22'].copy()
    winter_week = df.loc[f'{year}-03-15':f'{year}-03-22'].copy()
    summer_day = df.loc[f'{year}-08-23'].copy()
    winter_day = df.loc[f'{year}-03-23'].copy()
    
    # Calculate available energy for each subset
    for subset in [summer_week, winter_week, summer_day, winter_day]:
        subset['available_energy'] = subset['production'] + subset['battery_charge']
    
    # 1. Energy production vs weather conditions
    weather_conditions = ['sun_intensity', 'temperature', 'humidity', 'cloud_cover', 'wind_speed']
    for condition in weather_conditions:
        plot_chart(df, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'year', kind='scatter')
        plot_chart(summer_week, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'week', kind='scatter')
        plot_chart(winter_week, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'week', kind='scatter')
        plot_chart(summer_day, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'day', kind='scatter')
        plot_chart(winter_day, condition, 'production', f'Energy Production vs {condition.capitalize()}', condition, 'Energy Production (kWh)', 'day', kind='scatter')
    
    # 2. Energy production versus consumption
    plot_chart(df, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'year')
    plot_chart(summer_week, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'week')
    plot_chart(winter_week, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'week')
    plot_chart(summer_day, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'day')
    plot_chart(winter_day, 'datetime', ['production', 'total_consumption'], 'Energy Production vs Consumption', 'Date', 'Energy (kWh)', 'day')
    
    # 3. Energy profile vs allocation
    energy_components = ['irrigation', 'servers', 'gpu']
    plot_chart(df, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'year', kind='area')
    plot_chart(summer_week, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'week', kind='area')
    plot_chart(winter_week, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'week', kind='area')
    plot_chart(summer_day, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'day', kind='area')
    plot_chart(winter_day, 'datetime', energy_components, 'Energy Profile vs Allocation', 'Date', 'Energy (kWh)', 'day', kind='area')
    
    # 4. Available energy vs energy profile
    plot_chart(df, 'datetime', ['available_energy', 'total_consumption', 'battery_charge'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'year')
    plot_chart(summer_week, 'datetime', ['available_energy', 'total_consumption', 'battery_charge'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'week')
    plot_chart(winter_week, 'datetime', ['available_energy', 'total_consumption', 'battery_charge'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'week')
    plot_chart(summer_day, 'datetime', ['available_energy', 'total_consumption', 'battery_charge'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'day')
    plot_chart(winter_day, 'datetime', ['available_energy', 'total_consumption', 'battery_charge'], 'Available Energy vs Energy Profile', 'Date', 'Energy (kWh)', 'day')

if __name__ == "__main__":
    generate_charts()

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from matplotlib.dates import DateFormatter
from collections import defaultdict
import math
import logging

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
    july_data = df['2023-08-15':'2023-09-01']
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
    monthly_data = df['2023-08-15':'2023-09-01']
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

    # Weekly plot (using Aug as an example)
    july_data = df['2023-08-15':'2023-08-18']
    july_data.plot(ax=ax2)
    ax2.set_title('Hourly Battery Charge and Energy Deficit (Aug 15-18)')
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
# Standard library imports
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
import os

# Set Numba environment variable
os.environ['NUMBA_DEBUG'] = '0'

# Local imports
from simulator import Simulator
from solar_park_simulator import SolarParkSimulator
from energy_profile import EnergyProfile
from battery_storage import BatteryStorage
from energy_management_system import EnergyManagementSystem
from weather_simulator import WeatherSimulator

# Visualization imports
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

# Reporting and plotting functions
from reporting import generate_report_off_grid
from visualization import generate_charts
from config import WeatherConfig, SolarParkConfig, BatteryConfig, EnergyProfileConfig, SimulationConfig, load_config

# Set up logging
from logging_config import setup_logging, get_logger, log_exceptions

@log_exceptions
def main():
    logger = get_logger(__name__)
    logger.debug("Logging initialized")
    logger.info("Starting simulation")
    logger.warning("This is a warning message")
    
    try:
        config = load_config()
        simulator = Simulator(config)
        results = simulator.run_annual_simulation()
        results_summary = simulator.generate_report(results)
        # Generate reports
        generate_report_off_grid(results_summary, simulator.solar_park, simulator.battery)
        # Generate charts
        generate_charts()  
        
        logger.info("Simulation completed successfully")
    except Exception as e:
        logger.error(f"Simulation failed: {str(e)}")
        raise

if __name__ == "__main__":
    setup_logging(file_level=logging.DEBUG, console_level=logging.WARNING)
    logging.getLogger('numba').setLevel(logging.WARNING)
    main()
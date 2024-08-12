# Standard library imports
import logging
import os

# Set Numba environment variable
os.environ['NUMBA_DEBUG'] = '0'

# Local imports
from simulator import Simulator

# Reporting and plotting functions
from reporting import generate_report_off_grid
from visualization import generate_charts
from config import load_config

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
#NEED FIX      generate_comprehensive_daily_report(day: int, weather_sim: WeatherSimulator, solar_park: SolarParkSimulator, energy_profile: EnergyProfile, battery: BatteryStorage, ems: EnergyManagementSystem)
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

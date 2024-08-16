# Standard library imports
import logging
import os
from datetime import datetime

# Set Numba environment variable
os.environ['NUMBA_DEBUG'] = '0'

# Local imports
from simulator import Simulator
from reporting import generate_report_off_grid, generate_comprehensive_daily_report
from visualization import generate_charts
from config import load_config
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
        generate_report_off_grid(
            results_summary, 
            simulator.solar_park, 
            simulator.battery,
            simulator.energy_profile,
            config
        )

        # Generate comprehensive daily reports for summer and winter days
        summer_day = 189  # Adjust as needed
        winter_day = 63    # Adjust as needed
        
        for day in [summer_day, winter_day]:
            daily_report = generate_comprehensive_daily_report(
                day,
                simulator.weather_simulator,
                simulator.solar_park,
                simulator.energy_profile,
                simulator.battery,
                simulator.ems
            )

            # Save the daily report
            reports_dir = 'reports'
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)
            season = "summer" if day == summer_day else "winter"
            daily_report_file = os.path.join(reports_dir, f'{season}_daily_report_day_{day}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
            with open(daily_report_file, 'w') as f:
                f.write(daily_report)
            
            logger.info(f"{season.capitalize()} daily report for day {day} saved to: {daily_report_file}")

        # Generate charts
        generate_charts(results_summary)  

        logger.info("Simulation completed successfully")
    except Exception as e:
        logger.error(f"Simulation failed: {str(e)}")
        raise

if __name__ == "__main__":
    setup_logging(file_level=logging.DEBUG, console_level=logging.WARNING)
    logging.getLogger('numba').setLevel(logging.WARNING)
    main()
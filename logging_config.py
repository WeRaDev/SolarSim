import logging
from functools import wraps
import os
from datetime import datetime

def setup_logging(log_dir='logs', level=None, file_level=None, console_level=None):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, 'simulation.log')
    
    # If old-style 'level' is provided, use it for both file and console
    if level is not None:
        file_level = file_level or level
        console_level = console_level or level
    else:
        # Default levels if not specified
        file_level = file_level or logging.DEBUG
        console_level = console_level or logging.WARNING

    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set to lowest level to capture all logs

    # Create separate log files for different components
    components = ['WeatherSimulator', 'SolarParkSimulator', 'EnergyProfile', 'BatteryStorage', 'EnergyManagementSystem']
    for component in components:
        handler = logging.FileHandler(os.path.join(log_dir, f'{component.lower()}.log'))
        handler.setLevel(file_level)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

    # Create a general log file
    general_handler = logging.FileHandler(os.path.join(log_dir, 'general.log'))
    general_handler.setLevel(file_level)
    general_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(general_handler)

    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)

    return logger

def get_logger(name):
    return logging.getLogger(name)
    
def log_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.exception(f"Exception occurred in {func.__name__}: {str(e)}")
            raise
    return wrapper

class SimulationError(Exception):
    """Base class for simulation-specific exceptions."""
    pass

class WeatherError(SimulationError):
    """Raised when there's an issue with weather data."""
    pass

class EnergyError(SimulationError):
    """Raised when there's an issue with energy calculations."""
    pass
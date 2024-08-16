import numpy as np
import pvlib
import datetime
import pandas as pd
import warnings
from typing import List, Dict, Any
from logging_config import log_exceptions, get_logger
from helper import DateHelper
from typing import Tuple

class WeatherSimulator:
    def __init__(self, location: str, year: int):
        self.logger = get_logger(self.__class__.__name__)
        self.location = location
        self.year = year
        self.latitude, self.longitude = self._get_coordinates(location)
        self.altitude = self._get_altitude(location)
        self.monthly_data = {
            'sun_hours': [7.18, 9.18, 10.07, 11.52, 13.34, 13.89, 14.0, 13.56, 11.19, 8.85, 7.38, 7.33],
            'temp': [10.45, 11.05, 13.47, 16.43, 21.09, 24.92, 27.79, 28.1, 25.4, 20.63, 14.55, 11.62],
            'humidity': [80.81, 78.19, 77.66, 73.91, 60.69, 52.84, 48.86, 47.07, 51.93, 60.7, 73.48, 76.96],
            'precipitation': [24.16, 27.53, 36.22, 41.97, 26.91, 6.36, 1.76, 2.97, 16.72, 40.79, 41.49, 25.15],
            'precipitation_days': [5.91, 5.45, 7.64, 7.91, 4.55, 1.36, 0.64, 1.0, 3.0, 5.0, 7.45, 4.36],
            'cloud_cover': [0.6, 0.55, 0.5, 0.45, 0.3, 0.2, 0.1, 0.15, 0.3, 0.45, 0.55, 0.6],
            'wind_speed': [4.5, 4.8, 5.2, 5.5, 5.0, 4.8, 4.5, 4.3, 4.0, 4.2, 4.5, 4.7]
        }
        self.days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    def _get_coordinates(self, location: str) -> Tuple[float, float]:
        coordinates = {
            "Beja, Portugal": (38.01667, -7.86667),  # Added Beja coordinates
            # Add more locations as needed
        }
        if location not in coordinates:
            self.logger.warning(f"Location {location} not found. Using default coordinates.")
            return 38.01506, -7.86323  # Default to Evora if location not found
        return coordinates[location]

    def _get_altitude(self, location: str) -> float:
        altitudes = {
            "Beja, Portugal": 278,  # Added Beja altitude
            # Add more locations as needed
        }
        if location not in altitudes:
            self.logger.warning(f"Altitude for {location} not found. Using default altitude.")
            return 245  # Default to Evora's altitude if location not found
        return altitudes[location]
    def safe_ineichen(self, apparent_zenith, airmass, linke_turbidity, altitude, dni_extra):
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            clearsky = pvlib.clearsky.ineichen(
                apparent_zenith, 
                airmass,
                linke_turbidity,
                altitude=altitude,
                dni_extra=dni_extra
            )
        return {'ghi': clearsky['ghi'], 'dni': clearsky['dni']}
    
    def _get_month(self, day_of_year: int) -> int:
        """Calculate the month from the day of the year."""
        cumulative_days = np.cumsum(self.days_in_month)
        return next(i for i, cd in enumerate(cumulative_days, 1) if day_of_year <= cd)

    @log_exceptions
    def simulate_hour(self, day_of_year: int, hour: int) -> Dict[str, Any]:
        self.logger.info("Starting hour simulation")
        month = self._get_month(day_of_year)
        
        # Interpolate daily values from monthly data
        sun_hours = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['sun_hours'])
        base_temp = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['temp'])
        humidity = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['humidity'])
        precipitation_prob = self.monthly_data['precipitation_days'][month - 1] / self.days_in_month[month - 1]
        cloud_cover = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['cloud_cover'])
        wind_speed = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['wind_speed'])

        date_time = pd.to_datetime(datetime.datetime(self.year, 1, 1) + datetime.timedelta(days=day_of_year - 1, hours=hour))
        date_time_index = pd.date_range(date_time, periods=1, freq='h')
        solar_position = pvlib.solarposition.get_solarposition(date_time_index, self.latitude, self.longitude)
        
        apparent_zenith = solar_position['apparent_zenith'].iloc[0]
        airmass = pvlib.atmosphere.get_relative_airmass(apparent_zenith)
        linke_turbidity = pvlib.clearsky.lookup_linke_turbidity(date_time_index, self.latitude, self.longitude)
        dni_extra = pvlib.irradiance.get_extra_radiation(date_time_index)
        
        clearsky = self.safe_ineichen(
            apparent_zenith, 
            airmass,
            linke_turbidity.iloc[0],
            altitude=self.altitude,
            dni_extra=dni_extra.iloc[0]
        )
        
        # Adjust for cloud cover (less aggressive reduction)
        cloud_factor = 1 - (0.75 * cloud_cover)
        ghi = clearsky['ghi'] * cloud_factor
        dni = clearsky['dni'] * cloud_factor
        
        # More sophisticated temperature model
        temp = base_temp + 5 * (ghi / 1000) - 2 * cloud_cover + np.random.normal(0, 1)
        
        # More sophisticated humidity model
        humidity = humidity - 10 * (ghi / 1000) + 20 * cloud_cover + np.random.normal(0, 5)
        humidity = np.clip(humidity, 0, 100)
        
        # Improved precipitation model
        rain_probability = 0.05 + 0.95 * (humidity / 100) ** 3  # Cubic relationship
        is_raining = np.random.random() < rain_probability
        
        # Adjust humidity if it's raining
        if is_raining:
            humidity = max(humidity, 80 + np.random.normal(0, 5))
        
        self.logger.info(f"Simulated GHI: {ghi}, DNI: {dni}")
        self.logger.info("Completed hour simulation")
        return {
            'ghi': ghi,
            'dni': dni,
            'temperature': temp,
            'humidity': humidity,
            'is_raining': is_raining,
            'cloud_cover': cloud_cover,
            'wind_speed': wind_speed,
            'airmass': airmass,
            'solar_zenith': apparent_zenith
        }

    def simulate_year(self) -> List[Dict[str, Any]]:
        self.logger.info("Start annual simulation")
        hourly_weather = []
        for day in range(DateHelper.get_days(self.year)):
            for hour in range(24):
                hour_weather = self.simulate_hour(day + 1, hour)
                hourly_weather.append(hour_weather)
        self.logger.info("Completed annual simulation")
        return hourly_weather

    def _cumulative_days(self) -> List[int]:
        return [sum(self.days_in_month[:i+1]) for i in range(12)]

    def _mid_month_days(self) -> List[int]:
        cum_days = [0] + self._cumulative_days()
        return [(cum_days[i] + cum_days[i+1]) // 2 for i in range(12)]

    def get_daily_data(self, day: int) -> Dict[str, List[float]]:
        daily_data = {
            'ghi': [], 'dni': [], 'temperature': [], 'humidity': [],
            'is_raining': [], 'cloud_cover': [], 'wind_speed': []
        }
        for hour in range(24):
            weather = self.simulate_hour(day + 1, hour)
            for key in daily_data:
                daily_data[key].append(weather[key])
        return daily_data
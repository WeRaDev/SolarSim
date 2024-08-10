import numpy as np
from typing import List, Dict, Any
from logging_config import log_exceptions, get_logger
from helper import DateHelper

class WeatherSimulator:
    def __init__(self, location: str, year: int):
        self.logger = get_logger(self.__class__.__name__)
        self.location = location
        self.year = year
        self.monthly_data = self.get_monthly_data()
        self.days_in_month = DateHelper.get_days_in_month(year)

    @staticmethod
    def get_monthly_data():
        return {
            'sun_hours': [7.18, 9.18, 10.07, 11.52, 13.34, 13.89, 14.0, 13.56, 11.19, 8.85, 7.38, 7.33],
            'temp': [10.45, 11.05, 13.47, 16.43, 21.09, 24.92, 27.79, 28.1, 25.4, 20.63, 14.55, 11.62],
            'humidity': [80.81, 78.19, 77.66, 73.91, 60.69, 52.84, 48.86, 47.07, 51.93, 60.7, 73.48, 76.96],
            'precipitation': [24.16, 27.53, 36.22, 41.97, 26.91, 6.36, 1.76, 2.97, 16.72, 40.79, 41.49, 25.15],
            'precipitation_days': [5.91, 5.45, 7.64, 7.91, 4.55, 1.36, 0.64, 1.0, 3.0, 5.0, 7.45, 4.36],
            'cloud_cover': [0.6, 0.55, 0.5, 0.45, 0.3, 0.2, 0.1, 0.15, 0.3, 0.45, 0.55, 0.6],
            'wind_speed': [4.5, 4.8, 5.2, 5.5, 5.0, 4.8, 4.5, 4.3, 4.0, 4.2, 4.5, 4.7]
        }
    


    @log_exceptions
    def simulate_hour(self, day_of_year: int, hour: int) -> Dict[str, Any]:
        month = next(m for m, days in enumerate(self._cumulative_days()) if day_of_year <= days) - 1
        self.logger.info("Starting hour simulation")
        # Interpolate daily values from monthly data
        sun_hours = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['sun_hours'])
        base_temp = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['temp'])
        humidity = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['humidity'])
        precipitation_prob = self.monthly_data['precipitation_days'][month] / self.days_in_month[month]
        cloud_cover = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['cloud_cover'])
        wind_speed = np.interp(day_of_year, self._mid_month_days(), self.monthly_data['wind_speed'])

        # Simulate hourly variations
        hour_angle = (hour - 12) * 15  # Solar hour angle
        sun_intensity = max(0, np.cos(np.radians(hour_angle))) * (sun_hours / 12)  # Adjust for actual sun hours
        
        # More sophisticated temperature model
        temp = base_temp + 5 * sun_intensity - 2 * cloud_cover + np.random.normal(0, 1)
        
        # More sophisticated humidity model
        humidity = humidity - 10 * sun_intensity + 20 * cloud_cover + np.random.normal(0, 5)
        humidity = np.clip(humidity, 0, 100)
        
        # Simplified precipitation model
        is_raining = np.random.random() < precipitation_prob
        self.logger.info("Completed hour simulation")
        return {
            'sun_intensity': sun_intensity,
            'temperature': temp,
            'humidity': humidity,
            'is_raining': is_raining,
            'cloud_cover': cloud_cover,
            'wind_speed': wind_speed
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
            'sun_intensity': [], 'temperature': [], 'humidity': [],
            'is_raining': [], 'cloud_cover': [], 'wind_speed': []
        }
        for hour in range(24):
            weather = self.simulate_hour(day + 1, hour)
            for key in daily_data:
                daily_data[key].append(weather[key])
        return daily_data
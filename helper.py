import numpy as np
from config import load_config
from calendar import isleap
from typing import List

class DateHelper:
    def __init__(self):
        pass

    @staticmethod
    def get_days_in_month(year: int) -> List[int]:
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if (isleap(year)):
            days_in_month[1] = 29
        return days_in_month
    
    @staticmethod
    def get_month(day: int) -> int:
        config = load_config()
        return np.searchsorted(np.cumsum(DateHelper.get_days_in_month(config.year)), day + 1)
    
    @staticmethod
    def get_hours(year: int) -> int:
        days_in_year = sum(DateHelper.get_days_in_month(year))
        return days_in_year * 24
    
    @staticmethod
    def get_days(year: int) -> int:
        days_in_year = sum(DateHelper.get_days_in_month(year))
        return days_in_year
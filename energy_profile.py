import numpy as np
from numba import jit
from logging_config import log_exceptions, get_logger
from config import EnergyProfileConfig
from typing import List

class EnergyProfile:
    def __init__(self, config: EnergyProfileConfig):
        self.logger = get_logger(self.__class__.__name__)
        self.pumps_power = config.pumps_power
        self.programmer_power = config.programmer_power
        self.dosing_pump_power = config.dosing_pump_power
        self.irrigation_months = np.array(config.irrigation_months)
        self.staking_nodes = config.staking_nodes
        self.staking_power = config.staking_power
        self.cooling_efficiency = config.cooling_efficiency
        self.gpu_power = config.gpu_power
        self.gpu_utilization_range = np.array(config.gpu_utilization_range)
        self.num_gpus = config.num_gpus

    @log_exceptions
    def irrigation_need(self, month: int, hour: int, weather: int):
        return self._irrigation_need_optimized(
            month, weather['is_raining'], self.irrigation_months,
            self.pumps_power, self.dosing_pump_power, self.programmer_power
        )

    @staticmethod
    @jit(nopython=True)
    def _irrigation_need_optimized(month: int, is_raining: bool, irrigation_months: List[int], pumps_power: float, dosing_pump_power: float, programmer_power: float):
        if month in irrigation_months and not is_raining:
            return pumps_power + dosing_pump_power + programmer_power
        return 0

    @log_exceptions
    def server_power_consumption(self, hour: int):
        return self._server_power_consumption_optimized(
            hour, self.staking_nodes, self.staking_power
        )

    @staticmethod
    @jit(nopython=True)
    def _server_power_consumption_optimized(hour: int, staking_nodes: int, staking_power: float) -> float:
        return staking_power * staking_nodes * (1 + 0.2 * np.sin(hour * np.pi / 12))

    @log_exceptions
    def gpu_power_consumption(self, available_energy: float):
        return self._gpu_power_consumption_optimized(
            available_energy, self.gpu_power, self.num_gpus, self.gpu_utilization_range
        )

    @staticmethod
    @jit(nopython=True)
    def _gpu_power_consumption_optimized(available_energy: float, gpu_power: float, num_gpus: int, gpu_utilization_range: List[float]):
        max_gpu_power = gpu_power * num_gpus
        utilization = min(1, available_energy / max_gpu_power)
        return max_gpu_power * utilization * np.random.uniform(gpu_utilization_range[0], gpu_utilization_range[1])
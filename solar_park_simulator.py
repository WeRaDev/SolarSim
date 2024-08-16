import numpy as np
import pandas as pd
import io
import os
import pvlib
from numba import jit
from typing import List, Dict, Any
from logging_config import log_exceptions, get_logger
from weather_simulator import WeatherSimulator

class SolarParkSimulator:
    def __init__(self, weather_simulator: WeatherSimulator, total_capacity: float, inverter_capacity: float, 
                 performance_ratio: float):
        self.logger = get_logger(self.__class__.__name__)
        self.total_capacity = total_capacity
        self.inverter_capacity = inverter_capacity
        self.num_inverters = 8
        self.single_inverter_capacity = 100 # 100 kW
        self.total_inverter_capacity = self.num_inverters * self.single_inverter_capacity  # W
        
        if self.total_inverter_capacity != self.inverter_capacity:
            self.logger.warning(f"Adjusting inverter capacity from {self.inverter_capacity} to {self.total_inverter_capacity} kW to match 8 inverters setup")
            self.inverter_capacity = self.total_inverter_capacity
        self.performance_ratio = performance_ratio
        self.weather_simulator = weather_simulator
        
        # Panel specifications
        self.panel_efficiency = 0.2
        self.temp_coefficient = -0.0035
        self.dust_factor = 0.98
        self.misc_losses = 0.97
        self.annual_degradation = 0.005
        self.years_in_operation = 0
        self.module_params = {
            'Name': 'Trina Solar TSM-420DEG15MC.20(II)',
            'Manufacturer': 'Trina Solar',
            'Technology': 'Mono-c-Si',
            'Bifacial': 1,
            'STC': 420.16,
            'PTC': 395.6,
            'A_c': 2.03,  # Module area
            'N_s': 44,  # Number of cells in series
            'I_sc_ref': 10.6,
            'V_oc_ref': 49.5,
            'I_mp_ref': 10.1,
            'V_mp_ref': 41.6,
            'alpha_sc': 0.005406,
            'beta_voc': -0.130185,
            'T_NOCT': 44,
            'a_ref': 1.80441,
            'I_L_ref': 10.7145,
            'I_o_ref': 1.2846e-11,
            'R_s': 0.221374,
            'R_sh_ref': 277.301,
            'Adjust': 4.71591,
            'gamma_r': -0.32,
            'Version': 'SAM 2018.11.11 r2',
            'Date': '11/16/2022'
        }
        self.temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass']
        
        # Load inverter parameters from local file
        inverter_file_path = os.path.join('data', 'CEC_Inverters.csv')  # Adjust the path as needed
        self.logger.info(f"Loading inverter parameters from: {inverter_file_path}")
        
        try:
            # Read the CSV file
            inverter_data = pd.read_csv(inverter_file_path, sep=';', skiprows=[1, 2])  # Skip units and [0] rows
            self.logger.info("Inverter data loaded successfully")
            self.logger.info(f"Number of inverter models: {len(inverter_data)}")
            
            # Find the specific inverter model we want
            inverter_name = 'Huawei Technologies Co - Ltd : SUN2000-100KTL-USH0 [800V]'
            inverter_row = inverter_data[inverter_data['Name'] == inverter_name]
            
            if inverter_row.empty:
                raise ValueError(f"Inverter model not found: {inverter_name}")
            
            # Convert the row to a dictionary
            self.inverter_params = inverter_row.iloc[0].to_dict()
            
            # Convert numeric values to float
            for key, value in self.inverter_params.items():
                if key not in ['Name', 'CEC_Date', 'CEC_hybrid']:
                    self.inverter_params[key] = float(value)
            
            self.logger.info("Inverter parameters:")
            self.logger.info(self.inverter_params)
        
        except FileNotFoundError:
            self.logger.error(f"Inverter parameter file not found: {inverter_file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading inverter parameters: {str(e)}")
            raise
        
        # Calculate the number of modules
        self.modules_count = int(self.total_capacity * 1000 / self.module_params['STC'])
        self.logger.info("Panels Count:")
        self.logger.info(self.modules_count)
        self.system = pvlib.pvsystem.PVSystem(
            surface_tilt=5,  # Assuming horizontal for simplicity, adjust as needed
            surface_azimuth=180,  # Assuming south-facing, adjust as needed
            module_parameters=self.module_params,
            inverter_parameters=self.inverter_params,
            modules_per_string=self.modules_count,
            strings_per_inverter=6
        )
        
    def calculate_cell_temperature(self, weather):
        return pvlib.temperature.sapm_cell(
            weather['ghi'],
            weather['temperature'],
            weather['wind_speed'],
            self.temperature_model_parameters['a'],
            self.temperature_model_parameters['b'],
            self.temperature_model_parameters['deltaT']
        )

    @log_exceptions
    def calculate_hourly_energy(self, weather):
        try:
            self.logger.info(f"Weather data: GHI={weather['ghi']}, DNI={weather['dni']}, Temp={weather['temperature']}")
            
            if weather['ghi'] == 0 and weather['dni'] == 0:
                self.logger.info("No sunlight, energy production is 0")
                return 0
    
            cell_temp = self.calculate_cell_temperature(weather)
            self.logger.info(f"Cell temperature: {cell_temp}")
            
            poa_irradiance = weather['ghi']
            self.logger.info(f"POA irradiance: {poa_irradiance}")
            
            # Calculate DC output using CEC model
            dc_params = pvlib.pvsystem.calcparams_cec(
                effective_irradiance=poa_irradiance,
                temp_cell=cell_temp,
                alpha_sc=self.module_params['alpha_sc'],
                a_ref=self.module_params['a_ref'],
                I_L_ref=self.module_params['I_L_ref'],
                I_o_ref=self.module_params['I_o_ref'],
                R_sh_ref=self.module_params['R_sh_ref'],
                R_s=self.module_params['R_s'],
                Adjust=self.module_params['Adjust']
            )
            dc_output = pvlib.pvsystem.singlediode(*dc_params)
            dc_power_module = dc_output['p_mp']
            dc_power_array = dc_power_module * self.modules_count
            self.logger.info(f"DC array output: {dc_power_array} W")
            
            # Calculate AC output using PVWatts inverter model
            pdc0 = float(self.inverter_params['Paco'])  # Nominal DC power, assumed to be equal to AC power rating
            ac_output = pvlib.inverter.pvwatts(pdc=dc_power_array, pdc0=pdc0, eta_inv_nom=0.96)
            
            self.logger.info(f"AC output: {ac_output} W")
            
            # Apply other factors
            degradation_factor = (1 - self.annual_degradation) ** self.years_in_operation
            humidity_adjustment = 1 - max(0, (weather['humidity'] - 70) * 0.002)
            rain_adjustment = 0.95 if weather['is_raining'] else 1
            
            energy_produced = (ac_output * self.performance_ratio * degradation_factor * 
                               humidity_adjustment * rain_adjustment * 
                               self.dust_factor * self.misc_losses) / 1000  # Convert to kWh
            
            self.logger.info(f"Energy produced, kWh: {energy_produced}")
            
            return min(energy_produced, self.inverter_capacity / 1000)  # in kWh
            
        except Exception as e:
            self.logger.error(f"Error in calculate_hourly_energy: {str(e)}")
            self.logger.exception("Exception details:")
            return 0
        
    def calculate_iec61724_metrics(self, weather_data, energy_production):
        total_ghi = sum(w['ghi'] for w in weather_data)
        total_energy = sum(energy_production)
        
        y_f = total_energy / self.total_capacity  # Final Yield
        y_r = total_ghi / 1000  # Reference Yield
        
        pr = y_f / y_r  # Performance Ratio
        
        return {
            'final_yield': y_f,
            'reference_yield': y_r,
            'performance_ratio': pr
        }
    def calculate_monthly_production(self, hourly_production: np.array) -> List[float]:
        days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        monthly_production = []
        start_idx = 0
        for days in days_in_month:
            end_idx = start_idx + days * 24
            month_prod = np.sum(hourly_production[start_idx:end_idx])
            monthly_production.append(month_prod)
            start_idx = end_idx
        
        for month, prod in enumerate(monthly_production, 1):
            self.logger.info(f"Month {month} production: {prod:.2f} kWh")
        
        return monthly_production
    
    def simulate_annual_production(self) -> Dict[str, Any]:
        self.logger.info("Starting annual simulation")
        weather_data = self.weather_simulator.simulate_year()
        hourly_production = np.array([self.calculate_hourly_energy(hour) for hour in weather_data])
        monthly_production = self.calculate_monthly_production(hourly_production)
        total_annual_production = np.sum(hourly_production)
        self.logger.info(f"Total annual production: {total_annual_production} kWh")
        specific_yield = total_annual_production / self.total_capacity
        self.logger.info(f"Specific Yield: {specific_yield} kWh/kWp")
        iec_metrics = self.calculate_iec61724_metrics(weather_data, hourly_production)
        self.logger.info(f"IEC 61724 Metrics: {iec_metrics}")
        self.logger.info("Complete annual simulation")
        return {
            'energy_production': hourly_production,
            'weather_data': weather_data,
            'total_annual_production': total_annual_production,
            'specific_yield': specific_yield,
            'iec_metrics': iec_metrics,
            'monthly_production': monthly_production
        }

    def get_daily_production(self, weather_data: Dict[str, List[float]]) -> List[float]:
        return [self.calculate_hourly_energy(
            {key: weather_data[key][i] for key in weather_data}
        ) for i in range(24)]
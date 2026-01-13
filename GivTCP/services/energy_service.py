"""
Energy Calculation Service for GivTCP.

Phase 3 Refactoring: Extract Service Layer

This service handles all energy-related calculations including:
- Total energy metrics (cumulative since system start)
- Daily energy metrics (today's values)
- Model-dependent load calculations (Hybrid vs non-Hybrid)
- Energy validation and midnight reset detection
"""

import logging
from givenergy_modbus.model.inverter import Model
from typing import Optional


logger = logging.getLogger(__name__)


class EnergyCalculationService:
    """
    Service for calculating energy metrics from inverter data.

    Handles both total (cumulative) and daily energy calculations,
    with model-specific logic for Hybrid vs non-Hybrid inverters.
    """

    def calculate_total_energy(self, inverter) -> dict:
        """
        Calculate cumulative energy metrics since system start.

        Args:
            inverter: Inverter object with energy register data

        Returns:
            dict: Total energy metrics with keys:
                - Export_Energy_Total_kWh
                - Import_Energy_Total_kWh
                - Invertor_Energy_Total_kWh
                - PV_Energy_Total_kWh
                - AC_Charge_Energy_Total_kWh
                - Load_Energy_Total_kWh (model-dependent calculation)
                - Self_Consumption_Energy_Total_kWh
        """
        logger.info("Calculating total energy data")

        total = {
            'Export_Energy_Total_kWh': inverter.e_grid_out_total,
            'Import_Energy_Total_kWh': inverter.e_grid_in_total,
            'Invertor_Energy_Total_kWh': inverter.e_inverter_out_total,
            'PV_Energy_Total_kWh': inverter.e_pv_total,
            'AC_Charge_Energy_Total_kWh': inverter.e_inverter_in_total
        }

        # Model-dependent load calculation
        total['Load_Energy_Total_kWh'] = self._calculate_load_energy(
            inverter_energy=total['Invertor_Energy_Total_kWh'],
            ac_charge_energy=total['AC_Charge_Energy_Total_kWh'],
            export_energy=total['Export_Energy_Total_kWh'],
            import_energy=total['Import_Energy_Total_kWh'],
            pv_energy=total['PV_Energy_Total_kWh'],
            model=inverter.inverter_model
        )

        # Self-consumption calculation
        total['Self_Consumption_Energy_Total_kWh'] = round(
            total['PV_Energy_Total_kWh'], 2
        ) - round(
            total['Export_Energy_Total_kWh'], 2
        )

        return total

    def calculate_daily_energy(self, inverter) -> dict:
        """
        Calculate today's energy metrics.

        Args:
            inverter: Inverter object with daily energy register data

        Returns:
            dict: Daily energy metrics with keys:
                - PV_Energy_Today_kWh
                - Import_Energy_Today_kWh
                - Export_Energy_Today_kWh
                - AC_Charge_Energy_Today_kWh
                - Invertor_Energy_Today_kWh
                - Self_Consumption_Energy_Today_kWh
                - Load_Energy_Today_kWh (model-dependent calculation)
        """
        logger.info("Calculating today's energy data")

        daily = {
            'PV_Energy_Today_kWh': inverter.e_pv1_day + inverter.e_pv2_day,
            'Import_Energy_Today_kWh': inverter.e_grid_in_day,
            'Export_Energy_Today_kWh': inverter.e_grid_out_day,
            'AC_Charge_Energy_Today_kWh': inverter.e_inverter_in_day,
            'Invertor_Energy_Today_kWh': inverter.e_inverter_out_day
        }

        # Self-consumption calculation
        daily['Self_Consumption_Energy_Today_kWh'] = round(
            daily['PV_Energy_Today_kWh'], 2
        ) - round(
            daily['Export_Energy_Today_kWh'], 2
        )

        # Model-dependent load calculation
        daily['Load_Energy_Today_kWh'] = self._calculate_load_energy(
            inverter_energy=daily['Invertor_Energy_Today_kWh'],
            ac_charge_energy=daily['AC_Charge_Energy_Today_kWh'],
            export_energy=daily['Export_Energy_Today_kWh'],
            import_energy=daily['Import_Energy_Today_kWh'],
            pv_energy=daily['PV_Energy_Today_kWh'],
            model=inverter.inverter_model
        )

        return daily

    def _calculate_load_energy(
        self,
        inverter_energy: float,
        ac_charge_energy: float,
        export_energy: float,
        import_energy: float,
        pv_energy: float,
        model: Model
    ) -> float:
        """
        Calculate load energy with model-specific logic.

        For Hybrid inverters:
            Load = (Inverter - AC_Charge) - (Export - Import)

        For non-Hybrid inverters:
            Load = (Inverter - AC_Charge) - (Export - Import) + PV

        Args:
            inverter_energy: Energy output from inverter
            ac_charge_energy: Energy used for AC charging
            export_energy: Energy exported to grid
            import_energy: Energy imported from grid
            pv_energy: Solar PV energy generated
            model: Inverter model (Hybrid or non-Hybrid)

        Returns:
            float: Calculated load energy in kWh (rounded to 2 decimal places)
        """
        net_inverter = inverter_energy - ac_charge_energy
        net_grid = export_energy - import_energy

        if model == Model.Hybrid:
            # Hybrid: Load = (Inverter - AC_Charge) - (Export - Import)
            load = net_inverter - net_grid
        else:
            # Non-Hybrid: Load = (Inverter - AC_Charge) - (Export - Import) + PV
            load = net_inverter - net_grid + pv_energy

        return round(load, 2)

    def check_for_midnight_reset(self, daily_energy: dict, system_time) -> bool:
        """
        Check if daily energy is zero at midnight (indicates daily reset).

        Args:
            daily_energy: Dictionary of daily energy values
            system_time: System datetime from inverter

        Returns:
            bool: True if midnight reset detected, False otherwise
        """
        checksum = sum(daily_energy.values())

        if checksum == 0 and system_time.hour == 0 and system_time.minute == 0:
            logger.info("Energy Today is Zero and it's midnight - midnight reset detected")
            return True

        return False

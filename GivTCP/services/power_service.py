"""
Power Calculation Service for GivTCP.

Phase 3 Refactoring: Extract Service Layer

This service handles all power-related calculations including:
- Core power measurements (PV, grid, inverter, load, EPS)
- Power validation with threshold checks
- Import/export power decomposition
- Power flow routing (solar→house/grid, grid→house)
- Self-consumption calculations
"""

import logging
from typing import Dict


logger = logging.getLogger(__name__)


class PowerCalculationService:
    """
    Service for calculating instantaneous power measurements and flows.

    Applies validation thresholds to detect and reject anomalous readings.
    Calculates power flow routing between solar, battery, house, and grid.
    """

    # Validation thresholds
    PV_POWER_MAX = 15000  # Maximum PV power in watts
    INVERTER_POWER_MIN = -6000  # Minimum inverter power (charging)
    INVERTER_POWER_MAX = 6000  # Maximum inverter power (discharging)
    LOAD_POWER_MAX = 15500  # Maximum load power in watts

    def calculate_power_stats(self, inverter) -> Dict[str, float]:
        """
        Calculate core power measurements with validation.

        Args:
            inverter: Inverter object with instantaneous power data

        Returns:
            dict: Power measurements including:
                - PV_Power_String_1, PV_Power_String_2, PV_Power
                - PV_Voltage_String_1, PV_Voltage_String_2
                - PV_Current_String_1, PV_Current_String_2
                - Grid_Power, Import_Power, Export_Power
                - EPS_Power
                - Invertor_Power, AC_Charge_Power
                - Load_Power
                - Self_Consumption_Power
        """
        logger.info("Calculating power statistics")
        power = {}

        # PV Power
        logger.info("Getting PV Power")
        pv_power_1 = inverter.p_pv1
        pv_power_2 = inverter.p_pv2
        pv_power = pv_power_1 + pv_power_2

        # Validate PV power (reject if > threshold)
        if pv_power < self.PV_POWER_MAX:
            power['PV_Power_String_1'] = pv_power_1
            power['PV_Power_String_2'] = pv_power_2
            power['PV_Power'] = pv_power

        # PV voltage and current (always include)
        power['PV_Voltage_String_1'] = inverter.v_pv1
        power['PV_Voltage_String_2'] = inverter.v_pv2
        power['PV_Current_String_1'] = inverter.i_pv1 * 10
        power['PV_Current_String_2'] = inverter.i_pv2 * 10

        # Grid Power - decompose into import/export
        logger.info("Getting Grid Power")
        grid_power = inverter.p_grid_out
        import_power, export_power = self._decompose_grid_power(grid_power)

        power['Grid_Power'] = grid_power
        power['Import_Power'] = import_power
        power['Export_Power'] = export_power

        # EPS (backup) Power
        logger.info("Getting EPS Power")
        power['EPS_Power'] = inverter.p_eps_backup

        # Invertor Power with validation
        logger.info("Getting Inverter Power")
        inverter_power = inverter.p_inverter_out

        # Only include if within valid range
        if self.INVERTER_POWER_MIN <= inverter_power <= self.INVERTER_POWER_MAX:
            power['Invertor_Power'] = inverter_power

        # AC Charge Power (negative inverter power)
        if inverter_power < 0:
            power['AC_Charge_Power'] = abs(inverter_power)
        else:
            power['AC_Charge_Power'] = 0

        # Load Power with validation
        logger.info("Getting Load Power")
        load_power = inverter.p_load_demand
        if load_power < self.LOAD_POWER_MAX:
            power['Load_Power'] = load_power

        # Self Consumption
        logger.info("Getting Self Consumption Power")
        power['Self_Consumption_Power'] = max(load_power - import_power, 0)

        return power

    def calculate_power_flows(self, power: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate power flow routing between solar, house, and grid.

        Note: Battery flows are calculated separately by BatteryMetricsService
        as they require battery-specific data.

        Args:
            power: Power dictionary from calculate_power_stats()

        Returns:
            dict: Power flows including:
                - Solar_to_House
                - Solar_to_Grid
                - Grid_to_House
        """
        logger.info("Calculating power flows")
        flows = {}

        pv_power = power.get('PV_Power', 0)
        load_power = power.get('Load_Power', 0)
        export_power = power.get('Export_Power', 0)
        import_power = power.get('Import_Power', 0)

        # Solar to House/Grid flows
        logger.info("Getting Solar to House/Grid Power Flows")
        if pv_power > 0:
            # Solar to House: minimum of PV production and load demand
            flows['Solar_to_House'] = min(pv_power, load_power)
            flows['Solar_to_Grid'] = export_power
        else:
            flows['Solar_to_House'] = 0
            flows['Solar_to_Grid'] = 0

        # Grid to House flow
        logger.info("Getting Grid to House Power Flow")
        if import_power > 0:
            flows['Grid_to_House'] = import_power
        else:
            flows['Grid_to_House'] = 0

        return flows

    def _decompose_grid_power(self, grid_power: float) -> tuple[float, float]:
        """
        Decompose grid power into import and export components.

        Grid power convention:
        - Negative value = importing from grid
        - Positive value = exporting to grid
        - Zero = no grid flow

        Args:
            grid_power: Net grid power (negative = import, positive = export)

        Returns:
            tuple: (import_power, export_power) both as positive values
        """
        if grid_power < 0:
            # Importing from grid
            import_power = abs(grid_power)
            export_power = 0
        elif grid_power > 0:
            # Exporting to grid
            import_power = 0
            export_power = abs(grid_power)
        else:
            # No grid flow
            import_power = 0
            export_power = 0

        return import_power, export_power

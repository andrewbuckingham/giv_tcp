"""
Battery Metrics Service for GivTCP.

Phase 3 Refactoring: Extract Service Layer

This service handles battery-specific calculations:
- SOC (State of Charge) in % and kWh
- Battery charge/discharge energy (today and total)
- Battery power decomposition
- Refined power flows (solar→battery, battery→house/grid, grid→battery)
- Per-battery hardware details (serial, capacity, cells, temps, voltages)
- Data validation (raise ValueError if all zeros)
"""

import logging
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class BatteryMetricsService:
    """
    Service for calculating battery metrics and flows.

    Handles SOC, energy, power, and detailed per-battery data extraction.
    Refines power flows to include battery routing information.
    """

    def calculate_battery_metrics(
        self,
        inverter,
        num_batteries: int,
        previous_soc: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate battery SOC, energy, and power metrics.

        Args:
            inverter: Inverter object with battery data
            num_batteries: Number of batteries in system
            previous_soc: Previous SOC value for fallback if current is zero

        Returns:
            dict: Battery metrics including:
                - SOC: Battery state of charge in %
                - SOC_kWh: Battery state of charge in kWh
                - Battery_Charge_Energy_Today_kWh
                - Battery_Discharge_Energy_Today_kWh
                - Battery_Throughput_Today_kWh
                - Battery_Charge_Energy_Total_kWh
                - Battery_Discharge_Energy_Total_kWh
                - Battery_Throughput_Total_kWh
                - Battery_Power: Net battery power (negative=charging)
                - Charge_Power: Charging power
                - Discharge_Power: Discharging power
        """
        if num_batteries == 0:
            return {}

        logger.info("Getting SOC")
        metrics = {}

        # SOC calculation with fallback
        soc = self._calculate_soc(inverter.battery_percent, previous_soc)
        metrics['SOC'] = soc

        # SOC in kWh
        battery_capacity_kwh = (inverter.battery_nominal_capacity * 51.2) / 1000
        metrics['SOC_kWh'] = (soc * battery_capacity_kwh) / 100

        # Battery energy (today)
        metrics['Battery_Charge_Energy_Today_kWh'] = inverter.e_battery_charge_day
        metrics['Battery_Discharge_Energy_Today_kWh'] = inverter.e_battery_discharge_day
        metrics['Battery_Throughput_Today_kWh'] = (
            inverter.e_battery_charge_day + inverter.e_battery_discharge_day
        )

        # Battery energy (total) - handle firmware version differences
        metrics['Battery_Throughput_Total_kWh'] = inverter.e_battery_throughput_total

        # Battery power decomposition
        battery_power = inverter.p_battery
        charge_power, discharge_power = self._decompose_battery_power(battery_power)

        metrics['Battery_Power'] = battery_power
        metrics['Charge_Power'] = charge_power
        metrics['Discharge_Power'] = discharge_power

        return metrics

    def get_battery_energy_totals(
        self,
        inverter,
        batteries: List
    ) -> Dict[str, float]:
        """
        Get total battery charge/discharge energy with firmware version handling.

        Some firmware versions report energy in different registers.
        If normal registers are zero, fall back to backup registers.

        Args:
            inverter: Inverter object
            batteries: List of battery objects

        Returns:
            dict: Total energy values
        """
        if (inverter.e_battery_charge_total == 0 and
            inverter.e_battery_discharge_total == 0 and
            len(batteries) > 0):
            # Use backup registers for some firmware versions
            return {
                'Battery_Charge_Energy_Total_kWh': batteries[0].e_battery_charge_total_2,
                'Battery_Discharge_Energy_Total_kWh': batteries[0].e_battery_discharge_total_2
            }
        else:
            return {
                'Battery_Charge_Energy_Total_kWh': inverter.e_battery_charge_total,
                'Battery_Discharge_Energy_Total_kWh': inverter.e_battery_discharge_total
            }

    def calculate_battery_flows(
        self,
        pv_power: float,
        load_power: float,
        export_power: float,
        import_power: float,
        charge_power: float,
        discharge_power: float
    ) -> Dict[str, float]:
        """
        Calculate refined power flows including battery routing.

        Refines the basic power flows to include battery-specific routing:
        - Solar to Battery
        - Battery to House
        - Battery to Grid
        - Grid to Battery

        Args:
            pv_power: PV power generation
            load_power: House load demand
            export_power: Power exported to grid
            import_power: Power imported from grid
            charge_power: Battery charging power
            discharge_power: Battery discharging power

        Returns:
            dict: Refined power flows
        """
        logger.info("Getting Solar to H/B/G Power Flows")
        flows = {}

        # Solar flows
        if pv_power > 0:
            # Solar to House: minimum of PV and load
            s2h = min(pv_power, load_power)
            flows['Solar_to_House'] = s2h

            # Solar to Battery: remaining PV after house and export
            s2b = max((pv_power - s2h) - export_power, 0)
            flows['Solar_to_Battery'] = s2b

            # Solar to Grid: remaining PV after house and battery
            flows['Solar_to_Grid'] = max(pv_power - s2h - s2b, 0)
        else:
            flows['Solar_to_House'] = 0
            flows['Solar_to_Battery'] = 0
            flows['Solar_to_Grid'] = 0

        # Battery to House
        logger.info("Getting Battery to House Power Flow")
        b2h = max(discharge_power - export_power, 0)
        flows['Battery_to_House'] = b2h

        # Grid to Battery/House
        logger.info("Getting Grid to Battery/House Power Flow")
        if import_power > 0:
            flows['Grid_to_Battery'] = charge_power - max(pv_power - load_power, 0)
            flows['Grid_to_House'] = max(import_power - charge_power, 0)
        else:
            flows['Grid_to_Battery'] = 0
            flows['Grid_to_House'] = 0

        # Battery to Grid
        logger.info("Getting Battery to Grid Power Flow")
        if export_power > 0:
            flows['Battery_to_Grid'] = max(discharge_power - b2h, 0)
        else:
            flows['Battery_to_Grid'] = 0

        return flows

    def get_battery_details(
        self,
        batteries: List,
        previous_battery_details: Optional[Dict] = None
    ) -> Dict[str, Dict]:
        """
        Extract detailed hardware information for each battery.

        Args:
            batteries: List of battery objects
            previous_battery_details: Previous battery details for fallback

        Returns:
            dict: Dictionary keyed by battery serial number with detailed info:
                - Battery_Serial_Number
                - Battery_SOC (with fallback if zero)
                - Battery_Capacity
                - Battery_Design_Capacity
                - Battery_Remaining_Capacity
                - Battery_Firmware_Version
                - Battery_Cells
                - Battery_Cycles
                - Battery_USB_present
                - Battery_Temperature
                - Battery_Voltage
                - Battery_Cell_1-16_Voltage
                - Battery_Cell_1-4_Temperature
        """
        logger.info("Getting Battery Details")
        battery_details = {}

        for b in batteries:
            logger.info("Building battery output: ")
            battery = {}

            battery['Battery_Serial_Number'] = b.battery_serial_number

            # SOC with fallback
            if b.battery_soc != 0:
                battery['Battery_SOC'] = b.battery_soc
            elif previous_battery_details and b.battery_serial_number in previous_battery_details:
                battery['Battery_SOC'] = previous_battery_details[b.battery_serial_number]['Battery_SOC']
            else:
                battery['Battery_SOC'] = 1

            # Capacity and status
            battery['Battery_Capacity'] = b.battery_full_capacity
            battery['Battery_Design_Capacity'] = b.battery_design_capacity
            battery['Battery_Remaining_Capacity'] = b.battery_remaining_capacity
            battery['Battery_Firmware_Version'] = b.bms_firmware_version
            battery['Battery_Cells'] = b.battery_num_cells
            battery['Battery_Cycles'] = b.battery_num_cycles
            battery['Battery_USB_present'] = b.usb_inserted

            # Temperature and voltage
            battery['Battery_Temperature'] = b.temp_bms_mos
            battery['Battery_Voltage'] = b.v_battery_cells_sum

            # Cell voltages (16 cells)
            battery['Battery_Cell_1_Voltage'] = b.v_battery_cell_01
            battery['Battery_Cell_2_Voltage'] = b.v_battery_cell_02
            battery['Battery_Cell_3_Voltage'] = b.v_battery_cell_03
            battery['Battery_Cell_4_Voltage'] = b.v_battery_cell_04
            battery['Battery_Cell_5_Voltage'] = b.v_battery_cell_05
            battery['Battery_Cell_6_Voltage'] = b.v_battery_cell_06
            battery['Battery_Cell_7_Voltage'] = b.v_battery_cell_07
            battery['Battery_Cell_8_Voltage'] = b.v_battery_cell_08
            battery['Battery_Cell_9_Voltage'] = b.v_battery_cell_09
            battery['Battery_Cell_10_Voltage'] = b.v_battery_cell_10
            battery['Battery_Cell_11_Voltage'] = b.v_battery_cell_11
            battery['Battery_Cell_12_Voltage'] = b.v_battery_cell_12
            battery['Battery_Cell_13_Voltage'] = b.v_battery_cell_13
            battery['Battery_Cell_14_Voltage'] = b.v_battery_cell_14
            battery['Battery_Cell_15_Voltage'] = b.v_battery_cell_15
            battery['Battery_Cell_16_Voltage'] = b.v_battery_cell_16

            # Cell temperatures (4 sensors)
            battery['Battery_Cell_1_Temperature'] = b.temp_battery_cells_1
            battery['Battery_Cell_2_Temperature'] = b.temp_battery_cells_2
            battery['Battery_Cell_3_Temperature'] = b.temp_battery_cells_3
            battery['Battery_Cell_4_Temperature'] = b.temp_battery_cells_4

            battery_details[b.battery_serial_number] = battery
            logger.info(f"Battery {b.battery_serial_number} added")

        return battery_details

    def validate_energy_data(self, energy_total: Dict[str, float]) -> None:
        """
        Validate that energy data is not all zeros.

        Raises ValueError if all energy values are zero, indicating
        a communication failure with the inverter.

        Args:
            energy_total: Dictionary of total energy values

        Raises:
            ValueError: If all values are zero
        """
        checksum = sum(energy_total.values())
        if checksum == 0:
            raise ValueError("All zeros returned by Invertor, skipping update")

    def _calculate_soc(
        self,
        current_soc: float,
        previous_soc: Optional[float] = None
    ) -> float:
        """
        Calculate SOC with fallback if current value is zero.

        Args:
            current_soc: Current SOC from inverter
            previous_soc: Previous SOC for fallback

        Returns:
            float: Validated SOC value
        """
        if current_soc != 0:
            return current_soc
        elif previous_soc is not None:
            logger.error(f"Battery SOC reported as: {current_soc}% so using previous value")
            return previous_soc
        else:
            logger.error(f"Battery SOC reported as: {current_soc}% and no previous value so setting to 1%")
            return 1

    def _decompose_battery_power(self, battery_power: float) -> tuple[float, float]:
        """
        Decompose battery power into charge and discharge components.

        Battery power convention:
        - Positive value = discharging
        - Negative value = charging
        - Zero = no battery flow

        Args:
            battery_power: Net battery power

        Returns:
            tuple: (charge_power, discharge_power) both as positive values
        """
        if battery_power >= 0:
            # Discharging
            discharge_power = abs(battery_power)
            charge_power = 0
        else:
            # Charging
            discharge_power = 0
            charge_power = abs(battery_power)

        return charge_power, discharge_power

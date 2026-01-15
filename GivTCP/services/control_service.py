"""
Control Mode Service for GivTCP.

Phase 3 Refactoring: Extract Service Layer

This service handles control mode detection and system configuration:
- Mode detection (Eco, Eco (Paused), Timed Demand, Timed Export, Unknown)
- Charge/discharge schedules and rates
- Battery reserves and target SOC
- Status flag detection (.FCRunning, .FERunning, etc.)
- Timeslot configuration extraction
- Inverter hardware details
"""

import logging
from os.path import exists
from typing import Dict, Optional


logger = logging.getLogger(__name__)


class ControlModeService:
    """
    Service for detecting control mode and extracting system configuration.

    Determines operating mode based on battery power mode, discharge enable,
    and SOC reserve settings. Extracts charge/discharge schedules, status flags,
    and inverter hardware details.
    """

    def detect_control_mode(self, inverter, cache_data: Optional[dict] = None) -> Dict[str, str]:
        """
        Determine current system operating mode and control settings.

        Args:
            inverter: Inverter object with control register data
            cache_data: Optional previous cache data for temp pause status

        Returns:
            dict: Control mode data including:
                - Mode: System mode (Eco, Timed Demand, etc.)
                - Battery_Power_Reserve: Minimum power reserve
                - Target_SOC: Charge target SOC
                - Enable_Charge_Schedule: "enable" or "disable"
                - Enable_Discharge_Schedule: "enable" or "disable"
                - Enable_Discharge: "enable" or "disable" based on SOC
                - Battery_Charge_Rate: Charge rate percentage
                - Battery_Discharge_Rate: Discharge rate percentage
                - Force_Charge: "Running" or "Normal"
                - Force_Export: "Running" or "Normal"
                - Temp_Pause_Charge: "Running" or "Normal"
                - Temp_Pause_Discharge: "Running" or "Normal"
        """
        logger.info("Getting mode control figures")

        # Charge/discharge schedule status
        charge_schedule = "enable" if inverter.enable_charge else "disable"
        discharge_schedule = "enable" if inverter.enable_discharge else "disable"

        # Battery reserves and targets
        battery_reserve = inverter.battery_discharge_min_power_reserve
        target_soc = inverter.charge_target_soc

        # Discharge enable based on current SOC vs reserve
        if inverter.battery_soc_reserve <= inverter.battery_percent:
            discharge_enable = "enable"
        else:
            discharge_enable = "disable"

        # Calculate charge/discharge rates (limit * 3, capped at 100%)
        discharge_rate = min(inverter.battery_discharge_limit * 3, 100)
        charge_rate = min(inverter.battery_charge_limit * 3, 100)

        # Classify mode
        logger.info("Calculating Mode...")
        mode = self._classify_mode(inverter)
        logger.info(f"Mode is: {mode}")

        # Build control mode dictionary
        controlmode = {
            'Mode': mode,
            'Battery_Power_Reserve': battery_reserve,
            'Target_SOC': target_soc,
            'Enable_Charge_Schedule': charge_schedule,
            'Enable_Discharge_Schedule': discharge_schedule,
            'Enable_Discharge': discharge_enable,
            'Battery_Charge_Rate': charge_rate,
            'Battery_Discharge_Rate': discharge_rate
        }

        # Get temp pause status from cache if available
        if cache_data and not isinstance(cache_data, int):
            if "Temp_Pause_Discharge" in cache_data.get("Control", {}):
                controlmode['Temp_Pause_Discharge'] = cache_data["Control"]["Temp_Pause_Discharge"]
            if "Temp_Pause_Charge" in cache_data.get("Control", {}):
                controlmode['Temp_Pause_Charge'] = cache_data["Control"]["Temp_Pause_Charge"]
        else:
            controlmode['Temp_Pause_Charge'] = "Normal"
            controlmode['Temp_Pause_Discharge'] = "Normal"

        # Check status flags
        controlmode.update(self._check_status_flags())

        return controlmode

    def get_timeslots(self, inverter) -> Dict[str, str]:
        """
        Extract charge and discharge timeslot configuration.

        Args:
            inverter: Inverter object with timeslot data

        Returns:
            dict: Timeslot data with ISO formatted times:
                - Discharge_start_time_slot_1/2
                - Discharge_end_time_slot_1/2
                - Charge_start_time_slot_1/2
                - Charge_end_time_slot_1/2
        """
        logger.info("Getting TimeSlot data")

        timeslots = {
            'Discharge_start_time_slot_1': inverter.discharge_slot_1[0].isoformat(),
            'Discharge_end_time_slot_1': inverter.discharge_slot_1[1].isoformat(),
            'Discharge_start_time_slot_2': inverter.discharge_slot_2[0].isoformat(),
            'Discharge_end_time_slot_2': inverter.discharge_slot_2[1].isoformat(),
            'Charge_start_time_slot_1': inverter.charge_slot_1[0].isoformat(),
            'Charge_end_time_slot_1': inverter.charge_slot_1[1].isoformat(),
            'Charge_start_time_slot_2': inverter.charge_slot_2[0].isoformat(),
            'Charge_end_time_slot_2': inverter.charge_slot_2[1].isoformat()
        }

        return timeslots

    def get_inverter_details(self, inverter) -> Dict[str, any]:
        """
        Extract inverter hardware details.

        Args:
            inverter: Inverter object with hardware data

        Returns:
            dict: Inverter details including:
                - Battery_Type: "Lithium" or "Lead Acid"
                - Battery_Capacity_kWh: Calculated capacity
                - Invertor_Serial_Number
                - Modbus_Version
                - Meter_Type: "EM115" or "EM418"
                - Invertor_Type: Model type
                - Invertor_Temperature: Heatsink temperature
        """
        logger.info("Getting Invertor Details")

        # Battery type mapping
        battery_type = "Lithium" if inverter.battery_type == 1 else "Lead Acid"

        # Meter type mapping
        meter_type = "EM115" if inverter.meter_type == 1 else "EM418"

        # Battery capacity calculation
        battery_capacity = (inverter.battery_nominal_capacity * 51.2) / 1000

        invertor = {
            'Battery_Type': battery_type,
            'Battery_Capacity_kWh': battery_capacity,
            'Invertor_Serial_Number': inverter.inverter_serial_number,
            'Modbus_Version': inverter.modbus_version,
            'Meter_Type': meter_type,
            'Invertor_Type': inverter.inverter_model,
            'Invertor_Temperature': inverter.temp_inverter_heatsink
        }

        return invertor

    def _classify_mode(self, inverter) -> str:
        """
        Classify system operating mode based on register values.

        Mode determination logic:
        - Eco: battery_power_mode=1, enable_discharge=False, soc_reserve=4
        - Eco (Paused): battery_power_mode=1, enable_discharge=False, soc_reserve=100
        - Timed Demand: battery_power_mode=1, enable_discharge=True, soc_reserve=100
        - Timed Export: battery_power_mode=0, enable_discharge=True, soc_reserve=100
        - Unknown: All other combinations

        Args:
            inverter: Inverter object with mode registers

        Returns:
            str: Mode name
        """
        if (inverter.battery_power_mode == 1 and
            inverter.enable_discharge == False and
            inverter.battery_soc_reserve == 4):
            return "Eco"

        elif (inverter.battery_power_mode == 1 and
              inverter.enable_discharge == False and
              inverter.battery_soc_reserve == 100):
            return "Eco (Paused)"

        elif (inverter.battery_power_mode == 1 and
              inverter.enable_discharge == True and
              inverter.battery_soc_reserve == 100):
            return "Timed Demand"

        elif (inverter.battery_power_mode == 0 and
              inverter.enable_discharge == True and
              inverter.battery_soc_reserve == 100):
            return "Timed Export"

        else:
            return "Unknown"

    def _check_status_flags(self) -> Dict[str, str]:
        """
        Check for status flag files indicating special operating modes.

        Status flags:
        - .FCRunning: Force Charge running
        - .FERunning: Force Export running
        - .tpcRunning: Temp Pause Charge running
        - .tpdRunning: Temp Pause Discharge running

        Returns:
            dict: Status flag values ("Running" or "Normal")
        """
        flags = {}

        if exists(".FCRunning"):
            logger.info("Force Charge is Running")
            flags['Force_Charge'] = "Running"
        else:
            flags['Force_Charge'] = "Normal"

        if exists(".FERunning"):
            logger.info("Force_Export is Running")
            flags['Force_Export'] = "Running"
        else:
            flags['Force_Export'] = "Normal"

        if exists(".tpcRunning"):
            logger.info("Temp Pause Charge is Running")
            flags['Temp_Pause_Charge'] = "Running"
        else:
            flags['Temp_Pause_Charge'] = "Normal"

        if exists(".tpdRunning"):
            logger.info("Temp_Pause_Discharge is Running")
            flags['Temp_Pause_Discharge'] = "Running"
        else:
            flags['Temp_Pause_Discharge'] = "Normal"

        return flags

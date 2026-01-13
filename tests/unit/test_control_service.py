"""
Unit tests for ControlModeService.

Tests for Phase 3 refactoring: Extract Service Layer

Critical tests:
- Mode detection (Eco, Eco (Paused), Timed Demand, Timed Export, Unknown)
- Charge/discharge schedules and rates
- Status flag detection
- Timeslot extraction
- Inverter hardware details
- Cache data handling for temp pause
"""

import pytest
from datetime import datetime, time
from unittest.mock import Mock, patch
from GivTCP.services import ControlModeService


class TestControlModeService:
    """Tests for ControlModeService."""

    @pytest.fixture
    def service(self):
        """Create a ControlModeService instance."""
        return ControlModeService()

    @pytest.fixture
    def mock_inverter_eco(self):
        """Create a mock inverter in Eco mode."""
        inverter = Mock()
        inverter.battery_power_mode = 1
        inverter.enable_discharge = False
        inverter.battery_soc_reserve = 4
        inverter.enable_charge = True
        inverter.battery_discharge_min_power_reserve = 10
        inverter.charge_target_soc = 100
        inverter.battery_percent = 50
        inverter.battery_discharge_limit = 20  # Will be * 3 = 60%
        inverter.battery_charge_limit = 30  # Will be * 3 = 90%
        # Timeslots
        inverter.discharge_slot_1 = (time(0, 0), time(6, 0))
        inverter.discharge_slot_2 = (time(12, 0), time(18, 0))
        inverter.charge_slot_1 = (time(2, 30), time(5, 30))
        inverter.charge_slot_2 = (time(14, 0), time(17, 0))
        # Hardware details
        inverter.battery_type = 1  # Lithium
        inverter.battery_nominal_capacity = 100
        inverter.inverter_serial_number = "SA1234567890"
        inverter.modbus_version = 3
        inverter.meter_type = 1  # EM115
        inverter.inverter_model = "Hybrid"
        inverter.temp_inverter_heatsink = 35.5
        return inverter

    def test_detect_control_mode_eco(self, service, mock_inverter_eco):
        """Test Eco mode detection."""
        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Mode'] == "Eco"
        assert result['Battery_Power_Reserve'] == 10
        assert result['Target_SOC'] == 100
        assert result['Enable_Charge_Schedule'] == "enable"
        assert result['Enable_Discharge_Schedule'] == "disable"
        assert result['Enable_Discharge'] == "enable"  # SOC (50) > reserve (4)

    def test_detect_control_mode_eco_paused(self, service, mock_inverter_eco):
        """Test Eco (Paused) mode detection."""
        mock_inverter_eco.battery_soc_reserve = 100

        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Mode'] == "Eco (Paused)"

    def test_detect_control_mode_timed_demand(self, service, mock_inverter_eco):
        """Test Timed Demand mode detection."""
        mock_inverter_eco.battery_power_mode = 1
        mock_inverter_eco.enable_discharge = True
        mock_inverter_eco.battery_soc_reserve = 100

        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Mode'] == "Timed Demand"

    def test_detect_control_mode_timed_export(self, service, mock_inverter_eco):
        """Test Timed Export mode detection."""
        mock_inverter_eco.battery_power_mode = 0
        mock_inverter_eco.enable_discharge = True
        mock_inverter_eco.battery_soc_reserve = 100

        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Mode'] == "Timed Export"

    def test_detect_control_mode_unknown(self, service, mock_inverter_eco):
        """Test Unknown mode for unrecognized combinations."""
        mock_inverter_eco.battery_power_mode = 2  # Invalid value
        mock_inverter_eco.enable_discharge = True
        mock_inverter_eco.battery_soc_reserve = 50

        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Mode'] == "Unknown"

    def test_charge_discharge_rates(self, service, mock_inverter_eco):
        """Test charge/discharge rate calculations (limit * 3, capped at 100)."""
        result = service.detect_control_mode(mock_inverter_eco)

        # Discharge: 20 * 3 = 60%
        assert result['Battery_Discharge_Rate'] == 60
        # Charge: 30 * 3 = 90%
        assert result['Battery_Charge_Rate'] == 90

    def test_charge_discharge_rates_capped_at_100(self, service, mock_inverter_eco):
        """Test rates capped at 100% when limit * 3 exceeds 100."""
        mock_inverter_eco.battery_discharge_limit = 50  # 50 * 3 = 150, should cap to 100
        mock_inverter_eco.battery_charge_limit = 40  # 40 * 3 = 120, should cap to 100

        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Battery_Discharge_Rate'] == 100
        assert result['Battery_Charge_Rate'] == 100

    def test_discharge_enable_based_on_soc(self, service, mock_inverter_eco):
        """Test discharge enable based on SOC vs reserve."""
        # SOC (50) > reserve (4) = enable
        result = service.detect_control_mode(mock_inverter_eco)
        assert result['Enable_Discharge'] == "enable"

        # SOC (30) < reserve (50) = disable
        mock_inverter_eco.battery_percent = 30
        mock_inverter_eco.battery_soc_reserve = 50
        result = service.detect_control_mode(mock_inverter_eco)
        assert result['Enable_Discharge'] == "disable"

    def test_charge_schedule_enable_disable(self, service, mock_inverter_eco):
        """Test charge schedule enable/disable."""
        mock_inverter_eco.enable_charge = True
        result = service.detect_control_mode(mock_inverter_eco)
        assert result['Enable_Charge_Schedule'] == "enable"

        mock_inverter_eco.enable_charge = False
        result = service.detect_control_mode(mock_inverter_eco)
        assert result['Enable_Charge_Schedule'] == "disable"

    @patch('GivTCP.services.control_service.exists')
    def test_status_flags_all_running(self, mock_exists, service, mock_inverter_eco):
        """Test status flags when all are running."""
        mock_exists.return_value = True  # All flag files exist

        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Force_Charge'] == "Running"
        assert result['Force_Export'] == "Running"
        assert result['Temp_Pause_Charge'] == "Running"
        assert result['Temp_Pause_Discharge'] == "Running"

    @patch('GivTCP.services.control_service.exists')
    def test_status_flags_all_normal(self, mock_exists, service, mock_inverter_eco):
        """Test status flags when none are running."""
        mock_exists.return_value = False  # No flag files exist

        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Force_Charge'] == "Normal"
        assert result['Force_Export'] == "Normal"
        assert result['Temp_Pause_Charge'] == "Normal"
        assert result['Temp_Pause_Discharge'] == "Normal"

    @patch('GivTCP.services.control_service.exists')
    def test_status_flags_selective(self, mock_exists, service, mock_inverter_eco):
        """Test status flags with only some running."""
        # Only .FCRunning and .tpdRunning exist
        def exists_side_effect(path):
            return path in [".FCRunning", ".tpdRunning"]

        mock_exists.side_effect = exists_side_effect

        result = service.detect_control_mode(mock_inverter_eco)

        assert result['Force_Charge'] == "Running"
        assert result['Force_Export'] == "Normal"
        assert result['Temp_Pause_Charge'] == "Normal"
        assert result['Temp_Pause_Discharge'] == "Running"

    def test_temp_pause_from_cache(self, service, mock_inverter_eco):
        """Test temp pause status from cache data."""
        cache_data = {
            "Control": {
                "Temp_Pause_Charge": "Running",
                "Temp_Pause_Discharge": "Normal"
            }
        }

        with patch('GivTCP.services.control_service.exists', return_value=False):
            result = service.detect_control_mode(mock_inverter_eco, cache_data)

        # Status flags should override cache (all Normal since files don't exist)
        assert result['Temp_Pause_Charge'] == "Normal"
        assert result['Temp_Pause_Discharge'] == "Normal"

    def test_temp_pause_no_cache(self, service, mock_inverter_eco):
        """Test temp pause defaults to Normal when no cache."""
        with patch('GivTCP.services.control_service.exists', return_value=False):
            result = service.detect_control_mode(mock_inverter_eco, cache_data=None)

        assert result['Temp_Pause_Charge'] == "Normal"
        assert result['Temp_Pause_Discharge'] == "Normal"

    def test_get_timeslots(self, service, mock_inverter_eco):
        """Test timeslot extraction in ISO format."""
        result = service.get_timeslots(mock_inverter_eco)

        assert result['Discharge_start_time_slot_1'] == "00:00:00"
        assert result['Discharge_end_time_slot_1'] == "06:00:00"
        assert result['Discharge_start_time_slot_2'] == "12:00:00"
        assert result['Discharge_end_time_slot_2'] == "18:00:00"
        assert result['Charge_start_time_slot_1'] == "02:30:00"
        assert result['Charge_end_time_slot_1'] == "05:30:00"
        assert result['Charge_start_time_slot_2'] == "14:00:00"
        assert result['Charge_end_time_slot_2'] == "17:00:00"

    def test_get_inverter_details_lithium_em115(self, service, mock_inverter_eco):
        """Test inverter details extraction with Lithium battery and EM115 meter."""
        result = service.get_inverter_details(mock_inverter_eco)

        assert result['Battery_Type'] == "Lithium"
        assert result['Battery_Capacity_kWh'] == 5.12  # (100 * 51.2) / 1000
        assert result['Invertor_Serial_Number'] == "SA1234567890"
        assert result['Modbus_Version'] == 3
        assert result['Meter_Type'] == "EM115"
        assert result['Invertor_Type'] == "Hybrid"
        assert result['Invertor_Temperature'] == 35.5

    def test_get_inverter_details_lead_acid_em418(self, service, mock_inverter_eco):
        """Test inverter details with Lead Acid battery and EM418 meter."""
        mock_inverter_eco.battery_type = 0  # Lead Acid
        mock_inverter_eco.meter_type = 0  # EM418

        result = service.get_inverter_details(mock_inverter_eco)

        assert result['Battery_Type'] == "Lead Acid"
        assert result['Meter_Type'] == "EM418"

    def test_battery_capacity_calculation(self, service, mock_inverter_eco):
        """Test battery capacity calculation formula."""
        mock_inverter_eco.battery_nominal_capacity = 250

        result = service.get_inverter_details(mock_inverter_eco)

        # (250 * 51.2) / 1000 = 12.8 kWh
        assert result['Battery_Capacity_kWh'] == 12.8

    def test_classify_mode_eco(self, service):
        """Test mode classification for Eco."""
        inverter = Mock()
        inverter.battery_power_mode = 1
        inverter.enable_discharge = False
        inverter.battery_soc_reserve = 4

        mode = service._classify_mode(inverter)

        assert mode == "Eco"

    def test_classify_mode_eco_paused(self, service):
        """Test mode classification for Eco (Paused)."""
        inverter = Mock()
        inverter.battery_power_mode = 1
        inverter.enable_discharge = False
        inverter.battery_soc_reserve = 100

        mode = service._classify_mode(inverter)

        assert mode == "Eco (Paused)"

    def test_classify_mode_timed_demand(self, service):
        """Test mode classification for Timed Demand."""
        inverter = Mock()
        inverter.battery_power_mode = 1
        inverter.enable_discharge = True
        inverter.battery_soc_reserve = 100

        mode = service._classify_mode(inverter)

        assert mode == "Timed Demand"

    def test_classify_mode_timed_export(self, service):
        """Test mode classification for Timed Export."""
        inverter = Mock()
        inverter.battery_power_mode = 0
        inverter.enable_discharge = True
        inverter.battery_soc_reserve = 100

        mode = service._classify_mode(inverter)

        assert mode == "Timed Export"

    def test_classify_mode_unknown(self, service):
        """Test mode classification for unknown combinations."""
        inverter = Mock()
        inverter.battery_power_mode = 1
        inverter.enable_discharge = True
        inverter.battery_soc_reserve = 50  # Not a standard value

        mode = service._classify_mode(inverter)

        assert mode == "Unknown"

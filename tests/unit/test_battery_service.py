"""
Unit tests for BatteryMetricsService.

Tests for Phase 3 refactoring: Extract Service Layer

Critical tests:
- SOC calculations (% and kWh)
- Battery energy (charge, discharge, throughput)
- Battery power decomposition
- Refined power flows (battery routing)
- Per-battery hardware details
- Data validation (all zeros)
- Fallback values for zero SOC
"""

import pytest
from unittest.mock import Mock
from GivTCP.services import BatteryMetricsService


class TestBatteryMetricsService:
    """Tests for BatteryMetricsService."""

    @pytest.fixture
    def service(self):
        """Create a BatteryMetricsService instance."""
        return BatteryMetricsService()

    @pytest.fixture
    def mock_inverter_with_battery(self):
        """Create a mock inverter with battery data."""
        inverter = Mock()
        inverter.battery_percent = 75
        inverter.battery_nominal_capacity = 100
        inverter.e_battery_charge_day = 5.2
        inverter.e_battery_discharge_day = 8.3
        inverter.e_battery_throughput_total = 1250.5
        inverter.e_battery_charge_total = 650.0
        inverter.e_battery_discharge_total = 600.5
        inverter.p_battery = 1500  # Discharging
        return inverter

    @pytest.fixture
    def mock_battery(self):
        """Create a mock battery object with detailed data."""
        battery = Mock()
        battery.battery_serial_number = "BX1234567890"
        battery.battery_soc = 75
        battery.battery_full_capacity = 160
        battery.battery_design_capacity = 170
        battery.battery_remaining_capacity = 120
        battery.bms_firmware_version = "3001"
        battery.battery_num_cells = 16
        battery.battery_num_cycles = 245
        battery.usb_inserted = False
        battery.temp_bms_mos = 25.5
        battery.v_battery_cells_sum = 51.2
        # Cell voltages
        battery.v_battery_cell_01 = 3.20
        battery.v_battery_cell_02 = 3.21
        battery.v_battery_cell_03 = 3.19
        battery.v_battery_cell_04 = 3.20
        battery.v_battery_cell_05 = 3.20
        battery.v_battery_cell_06 = 3.21
        battery.v_battery_cell_07 = 3.20
        battery.v_battery_cell_08 = 3.19
        battery.v_battery_cell_09 = 3.20
        battery.v_battery_cell_10 = 3.21
        battery.v_battery_cell_11 = 3.20
        battery.v_battery_cell_12 = 3.20
        battery.v_battery_cell_13 = 3.19
        battery.v_battery_cell_14 = 3.21
        battery.v_battery_cell_15 = 3.20
        battery.v_battery_cell_16 = 3.20
        # Cell temperatures
        battery.temp_battery_cells_1 = 24.5
        battery.temp_battery_cells_2 = 25.0
        battery.temp_battery_cells_3 = 24.8
        battery.temp_battery_cells_4 = 25.2
        # Backup energy registers
        battery.e_battery_charge_total_2 = 0
        battery.e_battery_discharge_total_2 = 0
        return battery

    def test_calculate_battery_metrics_typical(self, service, mock_inverter_with_battery):
        """Test battery metrics calculation with typical values."""
        result = service.calculate_battery_metrics(
            mock_inverter_with_battery,
            num_batteries=1
        )

        assert result['SOC'] == 75
        assert result['SOC_kWh'] == 3.84  # (75 * 5.12) / 100
        assert result['Battery_Charge_Energy_Today_kWh'] == 5.2
        assert result['Battery_Discharge_Energy_Today_kWh'] == 8.3
        assert result['Battery_Throughput_Today_kWh'] == 13.5  # 5.2 + 8.3
        assert result['Battery_Throughput_Total_kWh'] == 1250.5
        assert result['Battery_Power'] == 1500
        assert result['Charge_Power'] == 0
        assert result['Discharge_Power'] == 1500

    def test_calculate_battery_metrics_no_batteries(self, service, mock_inverter_with_battery):
        """Test that no metrics are returned when num_batteries is 0."""
        result = service.calculate_battery_metrics(
            mock_inverter_with_battery,
            num_batteries=0
        )

        assert result == {}

    def test_soc_calculation_with_fallback(self, service, mock_inverter_with_battery):
        """Test SOC calculation with fallback when current SOC is zero."""
        mock_inverter_with_battery.battery_percent = 0

        result = service.calculate_battery_metrics(
            mock_inverter_with_battery,
            num_batteries=1,
            previous_soc=50.0
        )

        # Should use previous SOC
        assert result['SOC'] == 50.0

    def test_soc_calculation_no_fallback(self, service, mock_inverter_with_battery):
        """Test SOC defaults to 1 when zero and no previous value."""
        mock_inverter_with_battery.battery_percent = 0

        result = service.calculate_battery_metrics(
            mock_inverter_with_battery,
            num_batteries=1,
            previous_soc=None
        )

        # Should default to 1%
        assert result['SOC'] == 1

    def test_battery_power_discharging(self, service, mock_inverter_with_battery):
        """Test battery power decomposition when discharging (positive)."""
        mock_inverter_with_battery.p_battery = 2500

        result = service.calculate_battery_metrics(
            mock_inverter_with_battery,
            num_batteries=1
        )

        assert result['Battery_Power'] == 2500
        assert result['Discharge_Power'] == 2500
        assert result['Charge_Power'] == 0

    def test_battery_power_charging(self, service, mock_inverter_with_battery):
        """Test battery power decomposition when charging (negative)."""
        mock_inverter_with_battery.p_battery = -3000

        result = service.calculate_battery_metrics(
            mock_inverter_with_battery,
            num_batteries=1
        )

        assert result['Battery_Power'] == -3000
        assert result['Charge_Power'] == 3000
        assert result['Discharge_Power'] == 0

    def test_battery_power_zero(self, service, mock_inverter_with_battery):
        """Test battery power when zero (no flow)."""
        mock_inverter_with_battery.p_battery = 0

        result = service.calculate_battery_metrics(
            mock_inverter_with_battery,
            num_batteries=1
        )

        assert result['Battery_Power'] == 0
        assert result['Charge_Power'] == 0
        assert result['Discharge_Power'] == 0

    def test_get_battery_energy_totals_normal_registers(self, service, mock_inverter_with_battery):
        """Test battery energy totals from normal registers."""
        batteries = []

        result = service.get_battery_energy_totals(mock_inverter_with_battery, batteries)

        assert result['Battery_Charge_Energy_Total_kWh'] == 650.0
        assert result['Battery_Discharge_Energy_Total_kWh'] == 600.5

    def test_get_battery_energy_totals_backup_registers(self, service, mock_inverter_with_battery):
        """Test battery energy totals from backup registers when normal are zero."""
        mock_inverter_with_battery.e_battery_charge_total = 0
        mock_inverter_with_battery.e_battery_discharge_total = 0

        mock_battery = Mock()
        mock_battery.e_battery_charge_total_2 = 450.0
        mock_battery.e_battery_discharge_total_2 = 420.0
        batteries = [mock_battery]

        result = service.get_battery_energy_totals(mock_inverter_with_battery, batteries)

        # Should use backup registers
        assert result['Battery_Charge_Energy_Total_kWh'] == 450.0
        assert result['Battery_Discharge_Energy_Total_kWh'] == 420.0

    def test_calculate_battery_flows_with_solar(self, service):
        """Test battery flows with active solar generation."""
        flows = service.calculate_battery_flows(
            pv_power=5000,
            load_power=3000,
            export_power=500,
            import_power=0,
            charge_power=0,
            discharge_power=0
        )

        # Solar to House = min(5000, 3000) = 3000
        assert flows['Solar_to_House'] == 3000
        # Solar to Battery = (5000 - 3000) - 500 = 1500
        assert flows['Solar_to_Battery'] == 1500
        # Solar to Grid = 5000 - 3000 - 1500 = 500
        assert flows['Solar_to_Grid'] == 500

    def test_calculate_battery_flows_no_solar(self, service):
        """Test battery flows with no solar generation."""
        flows = service.calculate_battery_flows(
            pv_power=0,
            load_power=3000,
            export_power=0,
            import_power=2500,
            charge_power=0,
            discharge_power=2000
        )

        assert flows['Solar_to_House'] == 0
        assert flows['Solar_to_Battery'] == 0
        assert flows['Solar_to_Grid'] == 0
        assert flows['Battery_to_House'] == 2000  # discharge - export
        assert flows['Grid_to_House'] == 2500  # import - charge

    def test_calculate_battery_flows_battery_to_house(self, service):
        """Test battery to house flow calculation."""
        flows = service.calculate_battery_flows(
            pv_power=0,
            load_power=3000,
            export_power=500,
            import_power=0,
            charge_power=0,
            discharge_power=2500
        )

        # Battery to House = max(2500 - 500, 0) = 2000
        assert flows['Battery_to_House'] == 2000

    def test_calculate_battery_flows_battery_to_grid(self, service):
        """Test battery to grid flow calculation."""
        flows = service.calculate_battery_flows(
            pv_power=0,
            load_power=1000,
            export_power=1500,
            import_power=0,
            charge_power=0,
            discharge_power=2000
        )

        # Battery to House (B2H) = max(2000 - 1500, 0) = 500
        # Battery to Grid = max(2000 - 500, 0) = 1500
        assert flows['Battery_to_Grid'] == 1500

    def test_calculate_battery_flows_grid_to_battery(self, service):
        """Test grid to battery flow calculation."""
        flows = service.calculate_battery_flows(
            pv_power=1000,
            load_power=3000,
            export_power=0,
            import_power=2500,
            charge_power=1000,
            discharge_power=0
        )

        # Grid to Battery = charge_power - max(pv - load, 0)
        # = 1000 - max(1000 - 3000, 0) = 1000 - 0 = 1000
        assert flows['Grid_to_Battery'] == 1000

    def test_calculate_battery_flows_all_zeros(self, service):
        """Test battery flows with all zeros."""
        flows = service.calculate_battery_flows(
            pv_power=0,
            load_power=0,
            export_power=0,
            import_power=0,
            charge_power=0,
            discharge_power=0
        )

        assert flows['Solar_to_House'] == 0
        assert flows['Solar_to_Battery'] == 0
        assert flows['Solar_to_Grid'] == 0
        assert flows['Battery_to_House'] == 0
        assert flows['Battery_to_Grid'] == 0
        assert flows['Grid_to_Battery'] == 0
        assert flows['Grid_to_House'] == 0

    def test_get_battery_details(self, service, mock_battery):
        """Test extraction of battery details."""
        batteries = [mock_battery]

        result = service.get_battery_details(batteries)

        assert "BX1234567890" in result
        battery = result["BX1234567890"]

        assert battery['Battery_Serial_Number'] == "BX1234567890"
        assert battery['Battery_SOC'] == 75
        assert battery['Battery_Capacity'] == 160
        assert battery['Battery_Design_Capacity'] == 170
        assert battery['Battery_Remaining_Capacity'] == 120
        assert battery['Battery_Firmware_Version'] == "3001"
        assert battery['Battery_Cells'] == 16
        assert battery['Battery_Cycles'] == 245
        assert battery['Battery_USB_present'] == False
        assert battery['Battery_Temperature'] == 25.5
        assert battery['Battery_Voltage'] == 51.2

    def test_get_battery_details_cell_voltages(self, service, mock_battery):
        """Test extraction of all 16 cell voltages."""
        batteries = [mock_battery]

        result = service.get_battery_details(batteries)
        battery = result["BX1234567890"]

        # Verify all 16 cell voltages are present
        for i in range(1, 17):
            key = f'Battery_Cell_{i}_Voltage'
            assert key in battery
            assert isinstance(battery[key], float)

    def test_get_battery_details_cell_temperatures(self, service, mock_battery):
        """Test extraction of all 4 cell temperatures."""
        batteries = [mock_battery]

        result = service.get_battery_details(batteries)
        battery = result["BX1234567890"]

        assert battery['Battery_Cell_1_Temperature'] == 24.5
        assert battery['Battery_Cell_2_Temperature'] == 25.0
        assert battery['Battery_Cell_3_Temperature'] == 24.8
        assert battery['Battery_Cell_4_Temperature'] == 25.2

    def test_get_battery_details_multiple_batteries(self, service):
        """Test extraction of details for multiple batteries."""
        battery1 = Mock()
        battery1.battery_serial_number = "BX1111111111"
        battery1.battery_soc = 70
        battery1.battery_full_capacity = 160
        battery1.battery_design_capacity = 170
        battery1.battery_remaining_capacity = 112
        battery1.bms_firmware_version = "3001"
        battery1.battery_num_cells = 16
        battery1.battery_num_cycles = 100
        battery1.usb_inserted = False
        battery1.temp_bms_mos = 25.0
        battery1.v_battery_cells_sum = 51.0
        # Add cell voltages and temps
        for i in range(1, 17):
            setattr(battery1, f'v_battery_cell_{i:02d}', 3.2)
        for i in range(1, 5):
            setattr(battery1, f'temp_battery_cells_{i}', 25.0)

        battery2 = Mock()
        battery2.battery_serial_number = "BX2222222222"
        battery2.battery_soc = 75
        battery2.battery_full_capacity = 160
        battery2.battery_design_capacity = 170
        battery2.battery_remaining_capacity = 120
        battery2.bms_firmware_version = "3001"
        battery2.battery_num_cells = 16
        battery2.battery_num_cycles = 120
        battery2.usb_inserted = False
        battery2.temp_bms_mos = 26.0
        battery2.v_battery_cells_sum = 51.5
        # Add cell voltages and temps
        for i in range(1, 17):
            setattr(battery2, f'v_battery_cell_{i:02d}', 3.21)
        for i in range(1, 5):
            setattr(battery2, f'temp_battery_cells_{i}', 26.0)

        batteries = [battery1, battery2]

        result = service.get_battery_details(batteries)

        assert len(result) == 2
        assert "BX1111111111" in result
        assert "BX2222222222" in result
        assert result["BX1111111111"]['Battery_SOC'] == 70
        assert result["BX2222222222"]['Battery_SOC'] == 75

    def test_get_battery_details_zero_soc_with_previous(self, service, mock_battery):
        """Test battery details with zero SOC uses previous value."""
        mock_battery.battery_soc = 0
        batteries = [mock_battery]

        previous_details = {
            "BX1234567890": {
                "Battery_SOC": 65
            }
        }

        result = service.get_battery_details(batteries, previous_details)
        battery = result["BX1234567890"]

        # Should use previous SOC
        assert battery['Battery_SOC'] == 65

    def test_get_battery_details_zero_soc_no_previous(self, service, mock_battery):
        """Test battery details with zero SOC and no previous defaults to 1."""
        mock_battery.battery_soc = 0
        batteries = [mock_battery]

        result = service.get_battery_details(batteries, previous_battery_details=None)
        battery = result["BX1234567890"]

        # Should default to 1%
        assert battery['Battery_SOC'] == 1

    def test_validate_energy_data_passes(self, service):
        """Test validation passes when energy data has non-zero values."""
        energy_total = {
            'Export_Energy_Total_kWh': 1500.5,
            'Import_Energy_Total_kWh': 800.2,
            'PV_Energy_Total_kWh': 3000.0
        }

        # Should not raise
        service.validate_energy_data(energy_total)

    def test_validate_energy_data_fails_all_zeros(self, service):
        """Test validation raises ValueError when all energy data is zero."""
        energy_total = {
            'Export_Energy_Total_kWh': 0.0,
            'Import_Energy_Total_kWh': 0.0,
            'PV_Energy_Total_kWh': 0.0
        }

        with pytest.raises(ValueError, match="All zeros returned by Invertor"):
            service.validate_energy_data(energy_total)

    def test_decompose_battery_power_discharging(self, service):
        """Test battery power decomposition for discharging."""
        charge, discharge = service._decompose_battery_power(2000)

        assert charge == 0
        assert discharge == 2000

    def test_decompose_battery_power_charging(self, service):
        """Test battery power decomposition for charging."""
        charge, discharge = service._decompose_battery_power(-1500)

        assert charge == 1500
        assert discharge == 0

    def test_decompose_battery_power_zero(self, service):
        """Test battery power decomposition for zero."""
        charge, discharge = service._decompose_battery_power(0)

        assert charge == 0
        assert discharge == 0

    def test_soc_kwh_calculation(self, service, mock_inverter_with_battery):
        """Test SOC_kWh calculation formula."""
        # SOC = 75%, nominal_capacity = 100
        # battery_capacity_kwh = (100 * 51.2) / 1000 = 5.12 kWh
        # SOC_kWh = (75 * 5.12) / 100 = 3.84 kWh
        result = service.calculate_battery_metrics(
            mock_inverter_with_battery,
            num_batteries=1
        )

        assert result['SOC_kWh'] == pytest.approx(3.84, abs=0.01)

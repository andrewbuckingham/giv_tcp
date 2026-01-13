"""
Unit tests for PowerCalculationService.

Tests for Phase 3 refactoring: Extract Service Layer

Critical tests:
- Core power measurements
- Validation thresholds (PV, inverter, load)
- Grid power decomposition (import/export)
- Power flow calculations
- Edge cases (zeros, negatives, threshold boundaries)
"""

import pytest
from unittest.mock import Mock
from GivTCP.services import PowerCalculationService


class TestPowerCalculationService:
    """Tests for PowerCalculationService."""

    @pytest.fixture
    def service(self):
        """Create a PowerCalculationService instance."""
        return PowerCalculationService()

    @pytest.fixture
    def mock_inverter_typical(self):
        """Create a mock inverter with typical power values."""
        inverter = Mock()
        # PV power
        inverter.p_pv1 = 2500
        inverter.p_pv2 = 1800
        inverter.v_pv1 = 240
        inverter.v_pv2 = 235
        inverter.i_pv1 = 10.5
        inverter.i_pv2 = 7.8
        # Grid power (negative = import, positive = export)
        inverter.p_grid_out = 500  # Exporting
        # EPS power
        inverter.p_eps_backup = 0
        # Inverter power
        inverter.p_inverter_out = 3200
        # Load power
        inverter.p_load_demand = 4000
        return inverter

    def test_calculate_power_stats_typical_values(self, service, mock_inverter_typical):
        """Test power calculation with typical values."""
        result = service.calculate_power_stats(mock_inverter_typical)

        # PV power
        assert result['PV_Power_String_1'] == 2500
        assert result['PV_Power_String_2'] == 1800
        assert result['PV_Power'] == 4300
        assert result['PV_Voltage_String_1'] == 240
        assert result['PV_Voltage_String_2'] == 235
        assert result['PV_Current_String_1'] == 105.0  # 10.5 * 10
        assert result['PV_Current_String_2'] == 78.0  # 7.8 * 10

        # Grid power (exporting)
        assert result['Grid_Power'] == 500
        assert result['Import_Power'] == 0
        assert result['Export_Power'] == 500

        # EPS power
        assert result['EPS_Power'] == 0

        # Inverter power
        assert result['Invertor_Power'] == 3200
        assert result['AC_Charge_Power'] == 0

        # Load power
        assert result['Load_Power'] == 4000

        # Self-consumption
        assert result['Self_Consumption_Power'] == 4000  # Load - Import

    def test_pv_power_threshold_rejection(self, service, mock_inverter_typical):
        """Test that PV power above threshold is rejected."""
        mock_inverter_typical.p_pv1 = 8000
        mock_inverter_typical.p_pv2 = 8000  # Total = 16000 > 15000

        result = service.calculate_power_stats(mock_inverter_typical)

        # PV power values should NOT be in result (rejected)
        assert 'PV_Power_String_1' not in result
        assert 'PV_Power_String_2' not in result
        assert 'PV_Power' not in result

        # Voltage and current should still be included
        assert 'PV_Voltage_String_1' in result
        assert 'PV_Current_String_1' in result

    def test_pv_power_at_threshold_boundary(self, service, mock_inverter_typical):
        """Test PV power exactly at threshold."""
        mock_inverter_typical.p_pv1 = 7500
        mock_inverter_typical.p_pv2 = 7499  # Total = 14999 < 15000 (passes)

        result = service.calculate_power_stats(mock_inverter_typical)

        assert result['PV_Power'] == 14999

    def test_grid_power_import(self, service, mock_inverter_typical):
        """Test grid power when importing (negative value)."""
        mock_inverter_typical.p_grid_out = -1200  # Importing

        result = service.calculate_power_stats(mock_inverter_typical)

        assert result['Grid_Power'] == -1200
        assert result['Import_Power'] == 1200
        assert result['Export_Power'] == 0

    def test_grid_power_export(self, service, mock_inverter_typical):
        """Test grid power when exporting (positive value)."""
        mock_inverter_typical.p_grid_out = 800  # Exporting

        result = service.calculate_power_stats(mock_inverter_typical)

        assert result['Grid_Power'] == 800
        assert result['Import_Power'] == 0
        assert result['Export_Power'] == 800

    def test_grid_power_zero(self, service, mock_inverter_typical):
        """Test grid power when zero (no flow)."""
        mock_inverter_typical.p_grid_out = 0

        result = service.calculate_power_stats(mock_inverter_typical)

        assert result['Grid_Power'] == 0
        assert result['Import_Power'] == 0
        assert result['Export_Power'] == 0

    def test_inverter_power_within_range(self, service, mock_inverter_typical):
        """Test inverter power within valid range."""
        mock_inverter_typical.p_inverter_out = 3000

        result = service.calculate_power_stats(mock_inverter_typical)

        assert result['Invertor_Power'] == 3000

    def test_inverter_power_negative_within_range(self, service, mock_inverter_typical):
        """Test inverter power negative (charging) within valid range."""
        mock_inverter_typical.p_inverter_out = -2500

        result = service.calculate_power_stats(mock_inverter_typical)

        assert result['Invertor_Power'] == -2500
        assert result['AC_Charge_Power'] == 2500

    def test_inverter_power_above_threshold(self, service, mock_inverter_typical):
        """Test inverter power above threshold is rejected."""
        mock_inverter_typical.p_inverter_out = 7000  # > 6000

        result = service.calculate_power_stats(mock_inverter_typical)

        # Should NOT be included (rejected)
        assert 'Invertor_Power' not in result

    def test_inverter_power_below_threshold(self, service, mock_inverter_typical):
        """Test inverter power below threshold is rejected."""
        mock_inverter_typical.p_inverter_out = -7000  # < -6000

        result = service.calculate_power_stats(mock_inverter_typical)

        # Should NOT be included (rejected)
        assert 'Invertor_Power' not in result

    def test_inverter_power_at_threshold_boundaries(self, service, mock_inverter_typical):
        """Test inverter power at exact threshold boundaries."""
        # Test upper boundary
        mock_inverter_typical.p_inverter_out = 6000
        result = service.calculate_power_stats(mock_inverter_typical)
        assert result['Invertor_Power'] == 6000

        # Test lower boundary
        mock_inverter_typical.p_inverter_out = -6000
        result = service.calculate_power_stats(mock_inverter_typical)
        assert result['Invertor_Power'] == -6000
        assert result['AC_Charge_Power'] == 6000

    def test_load_power_within_threshold(self, service, mock_inverter_typical):
        """Test load power within valid range."""
        mock_inverter_typical.p_load_demand = 8000

        result = service.calculate_power_stats(mock_inverter_typical)

        assert result['Load_Power'] == 8000

    def test_load_power_above_threshold(self, service, mock_inverter_typical):
        """Test load power above threshold is rejected."""
        mock_inverter_typical.p_load_demand = 16000  # > 15500

        result = service.calculate_power_stats(mock_inverter_typical)

        # Should NOT be included (rejected)
        assert 'Load_Power' not in result

    def test_self_consumption_with_import(self, service, mock_inverter_typical):
        """Test self-consumption when importing from grid."""
        mock_inverter_typical.p_load_demand = 5000
        mock_inverter_typical.p_grid_out = -2000  # Importing 2000W

        result = service.calculate_power_stats(mock_inverter_typical)

        # Self-consumption = Load - Import = 5000 - 2000 = 3000
        assert result['Self_Consumption_Power'] == 3000

    def test_self_consumption_with_export(self, service, mock_inverter_typical):
        """Test self-consumption when exporting to grid."""
        mock_inverter_typical.p_load_demand = 3000
        mock_inverter_typical.p_grid_out = 1500  # Exporting

        result = service.calculate_power_stats(mock_inverter_typical)

        # Self-consumption = Load - 0 (import) = 3000
        assert result['Self_Consumption_Power'] == 3000

    def test_self_consumption_prevents_negative(self, service, mock_inverter_typical):
        """Test self-consumption uses max(0, Load - Import)."""
        mock_inverter_typical.p_load_demand = 1000
        mock_inverter_typical.p_grid_out = -3000  # Importing 3000W (> load)

        result = service.calculate_power_stats(mock_inverter_typical)

        # Should be max(1000 - 3000, 0) = 0
        assert result['Self_Consumption_Power'] == 0

    def test_calculate_power_flows_with_solar(self, service):
        """Test power flows with active solar generation."""
        power = {
            'PV_Power': 4000,
            'Load_Power': 3000,
            'Export_Power': 500,
            'Import_Power': 0
        }

        flows = service.calculate_power_flows(power)

        # Solar to House = min(PV, Load) = min(4000, 3000) = 3000
        assert flows['Solar_to_House'] == 3000
        assert flows['Solar_to_Grid'] == 500
        assert flows['Grid_to_House'] == 0

    def test_calculate_power_flows_no_solar(self, service):
        """Test power flows with no solar generation."""
        power = {
            'PV_Power': 0,
            'Load_Power': 3000,
            'Export_Power': 0,
            'Import_Power': 2500
        }

        flows = service.calculate_power_flows(power)

        assert flows['Solar_to_House'] == 0
        assert flows['Solar_to_Grid'] == 0
        assert flows['Grid_to_House'] == 2500

    def test_calculate_power_flows_high_load(self, service):
        """Test power flows when load exceeds solar."""
        power = {
            'PV_Power': 2000,
            'Load_Power': 5000,
            'Export_Power': 0,
            'Import_Power': 3000
        }

        flows = service.calculate_power_flows(power)

        # Solar to House = min(2000, 5000) = 2000 (all solar goes to house)
        assert flows['Solar_to_House'] == 2000
        assert flows['Solar_to_Grid'] == 0
        assert flows['Grid_to_House'] == 3000

    def test_calculate_power_flows_missing_keys(self, service):
        """Test power flows with missing power keys (defaults to 0)."""
        power = {}  # Empty dict

        flows = service.calculate_power_flows(power)

        # Should handle missing keys gracefully
        assert flows['Solar_to_House'] == 0
        assert flows['Solar_to_Grid'] == 0
        assert flows['Grid_to_House'] == 0

    def test_decompose_grid_power_import(self, service):
        """Test grid power decomposition for import."""
        import_power, export_power = service._decompose_grid_power(-1500)

        assert import_power == 1500
        assert export_power == 0

    def test_decompose_grid_power_export(self, service):
        """Test grid power decomposition for export."""
        import_power, export_power = service._decompose_grid_power(2000)

        assert import_power == 0
        assert export_power == 2000

    def test_decompose_grid_power_zero(self, service):
        """Test grid power decomposition for zero."""
        import_power, export_power = service._decompose_grid_power(0)

        assert import_power == 0
        assert export_power == 0

    def test_zero_power_values(self, service):
        """Test handling of all zero power values."""
        inverter = Mock()
        inverter.p_pv1 = 0
        inverter.p_pv2 = 0
        inverter.v_pv1 = 0
        inverter.v_pv2 = 0
        inverter.i_pv1 = 0
        inverter.i_pv2 = 0
        inverter.p_grid_out = 0
        inverter.p_eps_backup = 0
        inverter.p_inverter_out = 0
        inverter.p_load_demand = 0

        result = service.calculate_power_stats(inverter)

        # Should handle zeros gracefully
        assert result['PV_Power'] == 0
        assert result['Grid_Power'] == 0
        assert result['Invertor_Power'] == 0
        assert result['Load_Power'] == 0
        assert result['AC_Charge_Power'] == 0

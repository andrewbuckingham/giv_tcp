"""
Unit tests for EnergyCalculationService.

Tests for Phase 3 refactoring: Extract Service Layer

Critical tests:
- Total energy calculations
- Daily energy calculations
- Model-dependent load calculations (Hybrid vs non-Hybrid)
- Midnight reset detection
- Edge cases (zero values, negative values)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock
from givenergy_modbus.model.inverter import Model
from GivTCP.services import EnergyCalculationService


class TestEnergyCalculationService:
    """Tests for EnergyCalculationService."""

    @pytest.fixture
    def service(self):
        """Create an EnergyCalculationService instance."""
        return EnergyCalculationService()

    @pytest.fixture
    def mock_inverter_hybrid(self):
        """Create a mock Hybrid inverter with typical values."""
        inverter = Mock()
        inverter.inverter_model = Model.Hybrid
        # Total energy values
        inverter.e_grid_out_total = 1500.5
        inverter.e_grid_in_total = 800.2
        inverter.e_inverter_out_total = 2200.8
        inverter.e_pv_total = 3000.0
        inverter.e_inverter_in_total = 500.3
        # Daily energy values
        inverter.e_pv1_day = 10.5
        inverter.e_pv2_day = 8.3
        inverter.e_grid_in_day = 5.2
        inverter.e_grid_out_day = 12.1
        inverter.e_inverter_in_day = 2.5
        inverter.e_inverter_out_day = 18.7
        inverter.system_time = datetime(2026, 1, 13, 14, 30)
        return inverter

    @pytest.fixture
    def mock_inverter_nonhybrid(self):
        """Create a mock non-Hybrid inverter."""
        inverter = Mock()
        inverter.inverter_model = Model.AC
        # Total energy values
        inverter.e_grid_out_total = 2000.0
        inverter.e_grid_in_total = 1000.0
        inverter.e_inverter_out_total = 2500.0
        inverter.e_pv_total = 3500.0
        inverter.e_inverter_in_total = 600.0
        # Daily energy values
        inverter.e_pv1_day = 15.0
        inverter.e_pv2_day = 10.0
        inverter.e_grid_in_day = 8.0
        inverter.e_grid_out_day = 15.0
        inverter.e_inverter_in_day = 3.0
        inverter.e_inverter_out_day = 22.0
        inverter.system_time = datetime(2026, 1, 13, 14, 30)
        return inverter

    def test_calculate_total_energy_hybrid(self, service, mock_inverter_hybrid):
        """Test total energy calculation for Hybrid inverter."""
        result = service.calculate_total_energy(mock_inverter_hybrid)

        assert result['Export_Energy_Total_kWh'] == 1500.5
        assert result['Import_Energy_Total_kWh'] == 800.2
        assert result['Invertor_Energy_Total_kWh'] == 2200.8
        assert result['PV_Energy_Total_kWh'] == 3000.0
        assert result['AC_Charge_Energy_Total_kWh'] == 500.3

        # Verify self-consumption
        assert result['Self_Consumption_Energy_Total_kWh'] == round(3000.0 - 1500.5, 2)

        # Verify load calculation (Hybrid formula)
        # Load = (Inverter - AC_Charge) - (Export - Import)
        expected_load = round((2200.8 - 500.3) - (1500.5 - 800.2), 2)
        assert result['Load_Energy_Total_kWh'] == expected_load

    def test_calculate_total_energy_nonhybrid(self, service, mock_inverter_nonhybrid):
        """Test total energy calculation for non-Hybrid inverter."""
        result = service.calculate_total_energy(mock_inverter_nonhybrid)

        # Verify load calculation (non-Hybrid formula)
        # Load = (Inverter - AC_Charge) - (Export - Import) + PV
        expected_load = round((2500.0 - 600.0) - (2000.0 - 1000.0) + 3500.0, 2)
        assert result['Load_Energy_Total_kWh'] == expected_load

    def test_calculate_daily_energy_hybrid(self, service, mock_inverter_hybrid):
        """Test daily energy calculation for Hybrid inverter."""
        result = service.calculate_daily_energy(mock_inverter_hybrid)

        # Verify PV addition
        assert result['PV_Energy_Today_kWh'] == 18.8  # 10.5 + 8.3

        assert result['Import_Energy_Today_kWh'] == 5.2
        assert result['Export_Energy_Today_kWh'] == 12.1
        assert result['AC_Charge_Energy_Today_kWh'] == 2.5
        assert result['Invertor_Energy_Today_kWh'] == 18.7

        # Verify self-consumption (use approx due to floating point precision)
        assert result['Self_Consumption_Energy_Today_kWh'] == pytest.approx(6.7, abs=0.01)

        # Verify load calculation (Hybrid formula)
        expected_load = round((18.7 - 2.5) - (12.1 - 5.2), 2)
        assert result['Load_Energy_Today_kWh'] == expected_load

    def test_calculate_daily_energy_nonhybrid(self, service, mock_inverter_nonhybrid):
        """Test daily energy calculation for non-Hybrid inverter."""
        result = service.calculate_daily_energy(mock_inverter_nonhybrid)

        # Verify PV addition
        assert result['PV_Energy_Today_kWh'] == 25.0  # 15.0 + 10.0

        # Verify load calculation (non-Hybrid formula)
        expected_load = round((22.0 - 3.0) - (15.0 - 8.0) + 25.0, 2)
        assert result['Load_Energy_Today_kWh'] == expected_load

    def test_calculate_load_energy_hybrid_formula(self, service):
        """Test Hybrid load calculation formula."""
        load = service._calculate_load_energy(
            inverter_energy=100.0,
            ac_charge_energy=10.0,
            export_energy=30.0,
            import_energy=20.0,
            pv_energy=50.0,
            model=Model.Hybrid
        )

        # Hybrid: (100 - 10) - (30 - 20) = 90 - 10 = 80.0
        assert load == 80.0

    def test_calculate_load_energy_nonhybrid_formula(self, service):
        """Test non-Hybrid load calculation formula."""
        load = service._calculate_load_energy(
            inverter_energy=100.0,
            ac_charge_energy=10.0,
            export_energy=30.0,
            import_energy=20.0,
            pv_energy=50.0,
            model=Model.AC
        )

        # Non-Hybrid: (100 - 10) - (30 - 20) + 50 = 90 - 10 + 50 = 130.0
        assert load == 130.0

    def test_midnight_reset_detection_at_midnight_with_zeros(self, service):
        """Test midnight reset detection when all values are zero at midnight."""
        daily_energy = {
            'PV_Energy_Today_kWh': 0.0,
            'Import_Energy_Today_kWh': 0.0,
            'Export_Energy_Today_kWh': 0.0
        }
        system_time = datetime(2026, 1, 13, 0, 0)  # Midnight

        result = service.check_for_midnight_reset(daily_energy, system_time)

        assert result is True

    def test_midnight_reset_not_detected_at_midnight_with_values(self, service):
        """Test midnight reset NOT detected when values are non-zero at midnight."""
        daily_energy = {
            'PV_Energy_Today_kWh': 10.0,
            'Import_Energy_Today_kWh': 5.0,
            'Export_Energy_Today_kWh': 8.0
        }
        system_time = datetime(2026, 1, 13, 0, 0)  # Midnight

        result = service.check_for_midnight_reset(daily_energy, system_time)

        assert result is False

    def test_midnight_reset_not_detected_during_day_with_zeros(self, service):
        """Test midnight reset NOT detected when values are zero but not at midnight."""
        daily_energy = {
            'PV_Energy_Today_kWh': 0.0,
            'Import_Energy_Today_kWh': 0.0,
            'Export_Energy_Today_kWh': 0.0
        }
        system_time = datetime(2026, 1, 13, 14, 30)  # Daytime

        result = service.check_for_midnight_reset(daily_energy, system_time)

        assert result is False

    def test_midnight_reset_not_detected_at_0001(self, service):
        """Test midnight reset NOT detected at 00:01 (only 00:00 triggers)."""
        daily_energy = {
            'PV_Energy_Today_kWh': 0.0,
            'Import_Energy_Today_kWh': 0.0,
            'Export_Energy_Today_kWh': 0.0
        }
        system_time = datetime(2026, 1, 13, 0, 1)  # 00:01

        result = service.check_for_midnight_reset(daily_energy, system_time)

        assert result is False

    def test_zero_energy_values(self, service, mock_inverter_hybrid):
        """Test handling of zero energy values."""
        mock_inverter_hybrid.e_grid_out_total = 0.0
        mock_inverter_hybrid.e_grid_in_total = 0.0
        mock_inverter_hybrid.e_inverter_out_total = 0.0
        mock_inverter_hybrid.e_pv_total = 0.0
        mock_inverter_hybrid.e_inverter_in_total = 0.0

        result = service.calculate_total_energy(mock_inverter_hybrid)

        assert result['Export_Energy_Total_kWh'] == 0.0
        assert result['Import_Energy_Total_kWh'] == 0.0
        assert result['PV_Energy_Total_kWh'] == 0.0
        assert result['Load_Energy_Total_kWh'] == 0.0
        assert result['Self_Consumption_Energy_Total_kWh'] == 0.0

    def test_negative_values_handling(self, service):
        """Test handling of negative values (can occur with import/export)."""
        load = service._calculate_load_energy(
            inverter_energy=50.0,
            ac_charge_energy=10.0,
            export_energy=10.0,  # Export less than import
            import_energy=30.0,  # Net import
            pv_energy=20.0,
            model=Model.Hybrid
        )

        # Hybrid: (50 - 10) - (10 - 30) = 40 - (-20) = 60.0
        assert load == 60.0

    def test_large_values(self, service, mock_inverter_hybrid):
        """Test handling of large cumulative values."""
        mock_inverter_hybrid.e_grid_out_total = 99999.9
        mock_inverter_hybrid.e_grid_in_total = 88888.8
        mock_inverter_hybrid.e_pv_total = 150000.0

        result = service.calculate_total_energy(mock_inverter_hybrid)

        assert result['Export_Energy_Total_kWh'] == 99999.9
        assert result['PV_Energy_Total_kWh'] == 150000.0
        # Verify calculation doesn't overflow
        assert isinstance(result['Self_Consumption_Energy_Total_kWh'], float)

    def test_rounding_precision(self, service):
        """Test that load energy is rounded to 2 decimal places."""
        load = service._calculate_load_energy(
            inverter_energy=100.12345,
            ac_charge_energy=10.54321,
            export_energy=30.11111,
            import_energy=20.99999,
            pv_energy=50.88888,
            model=Model.Hybrid
        )

        # Verify result has at most 2 decimal places
        assert load == round(load, 2)
        # Verify it's actually rounded, not just truncated
        str_load = str(load)
        if '.' in str_load:
            decimals = len(str_load.split('.')[1])
            assert decimals <= 2

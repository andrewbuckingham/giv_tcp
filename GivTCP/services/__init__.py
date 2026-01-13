"""
Service layer for GivTCP inverter data processing.

Phase 3 Refactoring: Extract Service Layer

This module provides service classes that break down the monolithic getData()
function into testable, focused components with clear responsibilities.

Services:
- HardwareCommunicationService: Inverter communication with locking
- EnergyCalculationService: Total and daily energy calculations
- PowerCalculationService: Power stats and flow routing
- BatteryMetricsService: Battery-specific calculations and flows
- ControlModeService: Mode detection and configuration
- DataProcessingService: Post-processing, validation, and caching
"""

# Services will be imported here as they're created
from .hardware_service import HardwareCommunicationService
from .energy_service import EnergyCalculationService
from .power_service import PowerCalculationService
from .battery_service import BatteryMetricsService
from .control_service import ControlModeService
from .processing_service import DataProcessingService

__all__ = [
    'HardwareCommunicationService',
    'EnergyCalculationService',
    'PowerCalculationService',
    'BatteryMetricsService',
    'ControlModeService',
    'DataProcessingService',
]

"""
Data Processing Service for GivTCP.

Phase 3 Refactoring: Extract Service Layer

This service handles post-processing, validation, and caching:
- Rate calculations (tariff costs)
- Battery value tracking
- Data cleansing/smoothing against historical data
- Output consistency checks (compare keys with previous)
- Cache stack management (5-element FIFO)
- Cache persistence
"""

import logging
import pickle
from typing import Dict, List, Optional, Callable


logger = logging.getLogger(__name__)


class DataProcessingService:
    """
    Service for post-processing, validation, and caching of output data.

    Applies rate calculations, battery value tracking, data smoothing, and
    manages a 5-element FIFO cache stack for historical comparison.
    """

    def __init__(
        self,
        cache_repo=None,
        cache_file_path: Optional[str] = None,
        instance_id: str = "1",
        use_new_cache: bool = False,
        rate_calc_func: Optional[Callable] = None,
        battery_value_func: Optional[Callable] = None,
        data_cleansing_func: Optional[Callable] = None,
        dict_to_list_func: Optional[Callable] = None
    ):
        """
        Initialize data processing service.

        Args:
            cache_repo: CacheRepository instance (for new caching)
            cache_file_path: Path to cache pickle file (for legacy)
            instance_id: GivTCP instance identifier
            use_new_cache: Use new cache repository instead of pickle
            rate_calc_func: Function for rate calculations
            battery_value_func: Function for battery value calculations
            data_cleansing_func: Function for data smoothing
            dict_to_list_func: Function for flattening dict to list
        """
        self.cache_repo = cache_repo
        self.cache_file_path = cache_file_path
        self.instance_id = instance_id
        self.use_new_cache = use_new_cache
        self.rate_calc_func = rate_calc_func
        self.battery_value_func = battery_value_func
        self.data_cleansing_func = data_cleansing_func
        self.dict_to_list_func = dict_to_list_func

    def process_output(
        self,
        multi_output: Dict,
        cache_stack: List[Dict]
    ) -> Dict:
        """
        Apply post-processing pipeline to multi_output.

        Args:
            multi_output: New output data to process
            cache_stack: Current cache stack (5 elements)

        Returns:
            dict: Processed output data
        """
        logger.info("Processing output data")

        # Get previous output (most recent from cache stack)
        multi_output_old = cache_stack[4] if cache_stack and len(cache_stack) > 4 else multi_output

        # 1. Rate calculations
        if self.rate_calc_func:
            multi_output = self.rate_calc_func(multi_output, multi_output_old)

        # 2. Battery value calculations
        if self.battery_value_func:
            multi_output = self.battery_value_func(multi_output)

        # 3. Data cleansing/smoothing
        if self.data_cleansing_func and cache_stack and len(cache_stack) > 4:
            multi_output = self.data_cleansing_func(multi_output, cache_stack[4])

        # 4. Consistency check - warn if keys are missing
        if cache_stack and len(cache_stack) > 4:
            self._check_consistency(multi_output, cache_stack[4])

        return multi_output

    def update_cache_stack(
        self,
        cache_stack: List[Dict],
        new_data: Dict
    ) -> List[Dict]:
        """
        Update cache stack with new data (FIFO).

        Maintains a 5-element cache stack by removing oldest and adding newest.

        Args:
            cache_stack: Current cache stack
            new_data: New data to add

        Returns:
            list: Updated cache stack
        """
        # Remove oldest element
        if len(cache_stack) >= 5:
            cache_stack.pop(0)

        # Add new data
        cache_stack.append(new_data)

        return cache_stack

    def save_cache_stack(self, cache_stack: List[Dict]) -> None:
        """
        Persist cache stack to storage (repository or pickle).

        Args:
            cache_stack: Cache stack to save
        """
        if self.use_new_cache:
            # New: Use cache repository
            self.cache_repo.set('regCache_' + self.instance_id, cache_stack)
        else:
            # Legacy: Use pickle file
            with open(self.cache_file_path, 'wb') as outp:
                pickle.dump(cache_stack, outp, pickle.HIGHEST_PROTOCOL)

    def load_cache_stack(self) -> List[Dict]:
        """
        Load cache stack from storage (repository or pickle).

        Returns:
            list: Loaded cache stack, or empty 5-element list if not found
        """
        if self.use_new_cache:
            # New: Use cache repository
            cache_stack = self.cache_repo.get('regCache_' + self.instance_id)
            if cache_stack:
                return cache_stack
        else:
            # Legacy: Use pickle file
            try:
                with open(self.cache_file_path, 'rb') as inp:
                    return pickle.load(inp)
            except (FileNotFoundError, EOFError):
                pass

        # Return empty stack if not found
        return [0, 0, 0, 0, 0]

    def _check_consistency(
        self,
        new_data: Dict,
        old_data: Dict
    ) -> None:
        """
        Check consistency between new and old data keys.

        Logs critical warning if keys are missing from new data.

        Args:
            new_data: New output data
            old_data: Previous output data
        """
        if not self.dict_to_list_func:
            # Cannot check without dict_to_list function
            return

        # Flatten both dicts to lists of keys
        new_keys = set(self.dict_to_list_func(new_data))
        old_keys = set(self.dict_to_list_func(old_data))

        # Find keys that were in old but not in new
        missing_keys = old_keys - new_keys

        if len(missing_keys) > 0:
            for key in missing_keys:
                logger.critical(f"{key} is missing from new data, publishing all other data")

"""
Hardware Communication Service for GivTCP.

Phase 3 Refactoring: Extract Service Layer

This service handles inverter communication with proper locking:
- Lock acquisition (thread-safe or file-based)
- Inverter data retrieval via GivClient
- Timestamp tracking and updates
- Error handling
- Lock release
"""

import datetime
import logging
import pickle
from os.path import exists
from typing import Optional, NamedTuple


logger = logging.getLogger(__name__)


class InverterReadResult(NamedTuple):
    """Result of reading data from inverter."""
    inverter: object
    batteries: list
    timestamp: str
    time_since_last: float
    status: str


class HardwareCommunicationService:
    """
    Service for managing inverter hardware communication with locking.

    Coordinates lock acquisition, data retrieval from inverter via GivClient,
    and timestamp management. Supports both new lock manager and legacy
    file-based locking via feature flags.
    """

    def __init__(
        self,
        giv_client,
        lock_manager=None,
        cache_repo=None,
        lock_file_path: Optional[str] = None,
        last_update_path: Optional[str] = None,
        inverter_ip: str = "",
        instance_id: str = "1",
        use_new_locks: bool = False,
        use_new_cache: bool = False
    ):
        """
        Initialize hardware communication service.

        Args:
            giv_client: GivClient instance for inverter communication
            lock_manager: ThreadLockManager instance (for new locking)
            cache_repo: CacheRepository instance (for new caching)
            lock_file_path: Path to lock file (for legacy locking)
            last_update_path: Path to last update pickle (for legacy caching)
            inverter_ip: IP address of inverter
            instance_id: GivTCP instance identifier
            use_new_locks: Use new lock manager instead of file locks
            use_new_cache: Use new cache repository instead of pickle
        """
        self.giv_client = giv_client
        self.lock_manager = lock_manager
        self.cache_repo = cache_repo
        self.lock_file_path = lock_file_path
        self.last_update_path = last_update_path
        self.inverter_ip = inverter_ip
        self.instance_id = instance_id
        self.use_new_locks = use_new_locks
        self.use_new_cache = use_new_cache

    def read_inverter_data(self, fullrefresh: bool) -> InverterReadResult:
        """
        Read data from inverter with proper locking.

        Acquires lock (thread-safe or file-based), retrieves data via GivClient,
        tracks timestamps, and releases lock.

        Args:
            fullrefresh: Whether to perform full register refresh

        Returns:
            InverterReadResult with inverter, batteries, timestamp, and status

        Raises:
            TimeoutError: If lock acquisition times out (new locking only)
            Exception: If inverter communication fails
        """
        logger.info("Getting All Registers")

        if self.use_new_locks:
            return self._read_with_lock_manager(fullrefresh)
        else:
            return self._read_with_file_lock(fullrefresh)

    def _read_with_lock_manager(self, fullrefresh: bool) -> InverterReadResult:
        """
        Read inverter data using new ThreadLockManager.

        Args:
            fullrefresh: Whether to perform full register refresh

        Returns:
            InverterReadResult with data

        Raises:
            TimeoutError: If lock acquisition times out
        """
        try:
            with self.lock_manager.acquire('inverter_read', timeout=30.0):
                logger.info("Lock acquired for inverter read")
                logger.info(f"Connecting to: {self.inverter_ip}")

                # Get data from inverter
                plant = self.giv_client.getData(fullrefresh)
                inverter = plant.inverter
                batteries = plant.batteries

                # Lock will be released automatically when context exits
                logger.info("Lock released for inverter read")

                # Calculate timestamp and time since last update
                timestamp, time_since_last = self._update_timestamp()

                logger.info("Invertor connection successful, registers retrieved")

                return InverterReadResult(
                    inverter=inverter,
                    batteries=batteries,
                    timestamp=timestamp,
                    time_since_last=time_since_last,
                    status="online"
                )

        except TimeoutError:
            logger.error("Timeout waiting for inverter read lock")
            raise

    def _read_with_file_lock(self, fullrefresh: bool) -> InverterReadResult:
        """
        Read inverter data using legacy file-based locking.

        Args:
            fullrefresh: Whether to perform full register refresh

        Returns:
            InverterReadResult with data

        Raises:
            RuntimeError: If lockfile is already set
            Exception: If inverter communication fails
        """
        # Check for existing lock
        if exists(self.lock_file_path):
            logger.error("Lockfile set so aborting getData")
            raise RuntimeError("Lockfile set so aborting getData")

        # Create lock file
        logger.info("setting lock file")
        logger.info(f"Connecting to: {self.inverter_ip}")
        open(self.lock_file_path, 'w').close()

        try:
            # Get data from inverter
            plant = self.giv_client.getData(fullrefresh)
            inverter = plant.inverter
            batteries = plant.batteries

            # Calculate timestamp and time since last update
            timestamp, time_since_last = self._update_timestamp()

            logger.info("Invertor connection successful, registers retrieved")

            return InverterReadResult(
                inverter=inverter,
                batteries=batteries,
                timestamp=timestamp,
                time_since_last=time_since_last,
                status="online"
            )

        finally:
            # Always remove lock file, even on error
            logger.info("Removing lock file")
            if exists(self.lock_file_path):
                import os
                os.remove(self.lock_file_path)

    def _update_timestamp(self) -> tuple[str, float]:
        """
        Update timestamp and calculate time since last update.

        Uses cache repository (new) or pickle file (legacy) to track timestamps.

        Returns:
            tuple: (current_timestamp_iso, time_since_last_seconds)
        """
        # Get current timestamp
        current_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        timestamp = current_time.isoformat()

        # Calculate time since last update
        time_since_last = 0.0

        if self.use_new_cache:
            # New: Use cache repository
            previous_update = self.cache_repo.get('lastUpdate_' + self.instance_id)
            if previous_update:
                previous_time = datetime.datetime.fromisoformat(previous_update)
                timediff = current_time - previous_time
                time_since_last = (timediff.seconds * 1000000 + timediff.microseconds) / 1000000

            # Save new timestamp
            self.cache_repo.set('lastUpdate_' + self.instance_id, timestamp)

        else:
            # Legacy: Use pickle file
            if exists(self.last_update_path):
                with open(self.last_update_path, 'rb') as inp:
                    previous_update = pickle.load(inp)
                previous_time = datetime.datetime.fromisoformat(previous_update)
                timediff = current_time - previous_time
                time_since_last = (timediff.seconds * 1000000 + timediff.microseconds) / 1000000

            # Save new timestamp
            with open(self.last_update_path, 'wb') as outp:
                pickle.dump(timestamp, outp, pickle.HIGHEST_PROTOCOL)

        return timestamp, time_since_last

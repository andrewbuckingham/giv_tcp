# -*- coding: utf-8 -*-
"""
Utility functions for GivTCP.

This module contains pure functions extracted from read.py for better testability.
These functions have been separated to enable unit testing and improve code organization.

Extracted as part of Phase 1 refactoring: Establish Testing Infrastructure
"""

import datetime
import logging
from givenergy_modbus.model.inverter import Model

# Logger will be injected or imported from GivLUT
logger = logging.getLogger(__name__)


def dicttoList(array):
    """Convert nested dictionary keys to a flat list.

    Recursively extracts all keys from a nested dictionary structure and
    returns them as a flat list.

    Args:
        array: Dictionary to process (can be nested)

    Returns:
        List of all keys found in the dictionary and nested dictionaries

    Example:
        >>> dicttoList({"a": 1, "b": {"c": 2, "d": 3}})
        ['a', 'b', 'c', 'd']
    """
    safeoutput = []
    for p_load in array:
        output = array[p_load]
        safeoutput.append(p_load)
        if isinstance(output, dict):
            safeoutput = safeoutput + dicttoList(output)
    return safeoutput


def iterate_dict(array, logger_instance=None):
    """Create a publish-safe version of the output.

    Converts non-string or non-int datapoints to safe formats for publishing.
    Handles datetime, time, tuples, Model objects, and nested dictionaries.

    Args:
        array: Dictionary to process
        logger_instance: Optional logger instance (uses module logger if not provided)

    Returns:
        Dictionary with all values converted to publish-safe formats

    Note:
        - Datetime objects are converted to "DD-MM-YYYY HH:MM:SS" strings
        - Time objects are converted to "HH:MM" strings
        - Tuples with "slot" in key name are split into _start and _end
        - Model objects are converted to their name attribute
        - Floats are rounded to 3 decimal places
    """
    log = logger_instance or logger
    safeoutput = {}

    for p_load in array:
        output = array[p_load]

        if isinstance(output, dict):
            temp = iterate_dict(output, log)
            safeoutput[p_load] = temp
            log.info('Dealt with ' + p_load)

        elif isinstance(output, tuple):
            if "slot" in str(p_load):
                log.info('Converting Timeslots to publish safe string')
                safeoutput[p_load + "_start"] = output[0].strftime("%H:%M")
                safeoutput[p_load + "_end"] = output[1].strftime("%H:%M")
            else:
                # Deal with other tuples - Print each value
                for index, key in enumerate(output):
                    log.info('Converting Tuple to multiple publish safe strings')
                    safeoutput[p_load + "_" + str(index)] = str(key)

        elif isinstance(output, datetime.datetime):
            log.info('Converting datetime to publish safe string')
            safeoutput[p_load] = output.strftime("%d-%m-%Y %H:%M:%S")

        elif isinstance(output, datetime.time):
            log.info('Converting time to publish safe string')
            safeoutput[p_load] = output.strftime("%H:%M")

        elif isinstance(output, Model):
            log.info('Converting Model to publish safe string')
            safeoutput[p_load] = output.name

        elif isinstance(output, float):
            safeoutput[p_load] = round(output, 3)

        else:
            safeoutput[p_load] = output

    return safeoutput


def dataSmoother2(dataNew, dataOld, lastUpdate, givLUT, timezone, data_smoother_setting):
    """Perform data validation and smoothing to filter out spikes.

    This function validates new data against configured min/max bounds and
    applies smoothing to prevent sudden spikes that may be sensor errors.

    Args:
        dataNew: Tuple of (name, new_value)
        dataOld: Tuple of (name, old_value)
        lastUpdate: ISO format timestamp string of last update
        givLUT: Lookup table dictionary containing validation rules for each data point
        timezone: Timezone object for datetime calculations
        data_smoother_setting: Smoothing level setting ("high", "medium", "low", "none")

    Returns:
        The validated/smoothed data value (either new or old depending on validation)

    Validation Rules:
        - Values outside configured min/max bounds are rejected
        - Zero values are rejected if not allowed for that data type
        - Sudden spikes (>smoothRate change in <60 seconds) are rejected
        - Values that decrease when they should only increase are rejected
        - "Today" stats are accepted as-is at midnight
    """
    log = logger

    newData = dataNew[1]
    oldData = dataOld[1]
    name = dataNew[0]
    lookup = givLUT[name]

    # Determine smooth rate based on setting
    if data_smoother_setting.lower() == "high":
        smoothRate = 0.25
    elif data_smoother_setting.lower() == "medium":
        smoothRate = 0.35
    elif data_smoother_setting.lower() == "none":
        return newData
    else:
        smoothRate = 0.50

    # Only process numeric values
    if isinstance(newData, int) or isinstance(newData, float):
        if oldData != 0:
            then = datetime.datetime.fromisoformat(lastUpdate)
            now = datetime.datetime.now(timezone)

            # Special case: Today stats at midnight
            if now.minute == 0 and now.hour == 0 and "Today" in name:
                log.info("Midnight and " + str(name) + " so accepting value as is")
                return newData

            # Check if outside min and max ranges
            if newData < float(lookup.min) or newData > float(lookup.max):
                log.info(str(name) + " is outside of allowable bounds so using old value: " + str(newData))
                return oldData

            # Check if zero when not allowed
            if newData == 0 and not lookup.allowZero:
                log.info(str(name) + " is Zero so using old value")
                return oldData

            # Apply smoothing if required
            if lookup.smooth:
                if newData != oldData:  # Only if values differ
                    timeDelta = (now - then).total_seconds()
                    dataDelta = abs(newData - oldData) / oldData

                    if dataDelta > smoothRate and timeDelta < 60:
                        log.info(str(name) + " jumped too far in a single read: " +
                                str(oldData) + "->" + str(newData) + " so using previous value")
                        return oldData

            # Check if data should only increase
            if lookup.onlyIncrease:
                if (oldData - newData) > 0.11:
                    log.info(str(name) + " has decreased so using old value")
                    return oldData

    return newData

"""Utility functions to load and format embedded urls, extract module metadata"""
from datetime import datetime, timezone
from typing import Tuple

def get_module_metadata(unlock_time: str) -> Tuple[bool, str]:
    """Returns if module is locked and corresponding unlock time ("" if unlocked)"""
    locked=False
    formatted_datetime=""
    if unlock_time:
        # get formatted unlock time
        formatted_datetime = datetime.strptime(unlock_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc)
        # determine if locked
        locked = current_time < formatted_datetime

    return locked, formatted_datetime

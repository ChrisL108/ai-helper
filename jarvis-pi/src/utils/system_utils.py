import pytz
import logging
import platform
import psutil
from datetime import datetime
from typing import Dict, Any

# Initialize a cache variable
_cached_timezone = None

def get_time(timezone: str) -> str:
    """Get current time in specified timezone"""
    try:
        if timezone:
            tz = pytz.timezone(timezone)
        else:
            tz = pytz.timezone(_get_current_timezone())
        print(f"🔍 Timezone: {tz}")
        current_time = datetime.now(tz)
        return current_time.strftime("%I:%M %p %Z")
    except Exception as e:
        logging.error(f"Error getting time: {e}")
        return None

def _get_current_timezone() -> str:
    """Get system's current timezone in 'Region/City' format, with caching."""
    global _cached_timezone
    
    if _cached_timezone is not None:
        return _cached_timezone
    
    # Get the current time with timezone info
    current_time = datetime.now().astimezone()
    # Find the timezone name using pytz
    for tz in pytz.all_timezones:
        if datetime.now(pytz.timezone(tz)).utcoffset() == current_time.utcoffset():
            _cached_timezone = tz
            return tz
    
    _cached_timezone = "UTC"  # Fallback to UTC if no match is found
    return _cached_timezone

def get_system_info() -> Dict[str, Any]:
    print("🔍 Getting system info")
    """Get system information"""
    return {
        "os": platform.system(),
        "version": platform.version(),
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent
    }

def get_location() -> Dict[str, Any]:
    print("🔍 Getting location 🌎")
    """
    Get system location
    -- Not sure if this is a reliable approach
    """
    # TODO: Get location
    return "Somewhere over the rainbow"

def get_top_processes(limit=5):
    """Get top processes by CPU and memory usage."""
    print("🔍 Getting top processes")
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            if proc.info['cpu_percent'] is not None or proc.info['memory_percent'] is not None:
                processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by CPU and memory usage
    top_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]
    top_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:limit]

    return {
        "top_cpu": top_cpu,
        "top_memory": top_memory
    }

def humanize_time(timestamp: str) -> str:
    """Humanize a timestamp"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %I:%M %p")

basic_commands = {
    "time": lambda: get_time(),
    "date": lambda: datetime.now().strftime("%Y-%m-%d"),
    "hello": lambda: "At your service, wadup!",
    "goodbye": lambda: "Alright, peace!",
    "exit": lambda: "Shutting down.",
    "quit": lambda: "Shutting it down."
} 
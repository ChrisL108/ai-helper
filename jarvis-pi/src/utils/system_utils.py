import pytz
import logging
import platform
import psutil
from datetime import datetime
from typing import Dict, Any

def get_time(timezone: str) -> str:
    """Get current time in specified timezone"""
    try:
        tz = pytz.timezone(timezone)
        current_time = datetime.now(tz)
        return current_time.strftime("%I:%M %p %Z")
    except Exception as e:
        logging.error(f"Error getting time: {e}")
        return None

def get_current_timezone() -> str:
    """Get system's current timezone"""
    return str(datetime.now().astimezone().tzinfo)

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    return {
        "os": platform.system(),
        "version": platform.version(),
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent
    }

def get_location() -> Dict[str, Any]:
    """
    Get system location
    -- Not sure if this is a reliable approach
    """
    return {"timezone": get_current_timezone()}

basic_commands = {
    "time": lambda: get_time(get_current_timezone()),
    "date": lambda: datetime.now().strftime("%Y-%m-%d"),
    "hello": lambda: "Hello, how can I assist you today?",
    "goodbye": lambda: "Goodbye! Have a great day.",
    "exit": lambda: "Shutting down.",
    "quit": lambda: "Shutting it down."
} 
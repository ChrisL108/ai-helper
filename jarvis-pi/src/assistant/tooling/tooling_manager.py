from utils.system_utils import get_time, _get_current_timezone, get_system_info, get_location, get_top_processes, basic_commands
from assistant.tooling.helpers import format_messages_for_openai, extract_json_from_str
from assistant.news.youtube_channel_monitor import YouTubeChannelMonitor
from assistant.calendar_handler import CalendarHandler
from typing import Dict


class ToolingManager:
    def __init__(self):
        # Widgets
        self.calendar = CalendarHandler()
        self.news_monitor = YouTubeChannelMonitor()
        # Formatting / Helpers
        self.format_messages_for_openai = format_messages_for_openai
        self.extract_json_from_str = extract_json_from_str
        
        
    def execute_system_action(self, action_request: Dict) -> Dict[str, any]:
        """Execute a system action based on the action request"""
        action = action_request.get("action")
        parameters = action_request.get("parameters", {})
        
        # Get time
        if action == "get_time":
            timezone = parameters.get("timezone", _get_current_timezone())
            return {"send_direct": True, "result": get_time(timezone)}
        
        # Get system info
        elif action == "get_system_info":
            system_info = get_system_info()
            top_processes = get_top_processes(limit=5)
            result = f"System Info: {system_info if system_info else 'No system info available'}, Top Processes: {top_processes if top_processes else 'No top processes available'}"
            # print(f"🔍 {result}")
            return {"send_direct": False, "result": result}
        
        # Get location
        elif action == "get_location":
            return {"send_direct": False, "result": get_location()}
        
        # Get next calendar event
        elif action == "calendar_next_event":
            return {"send_direct": False, "result": self.calendar.next_event()}
        
        # Get events in timeframe
        elif action == "calendar_get_events":
            start_time = parameters.get("start_time")
            end_time = parameters.get("end_time")
            return {"send_direct": False, "result": self.calendar.get_events(start_time, end_time)}
        
        # Search for events
        elif action == "calendar_search":
            query = parameters.get("query")
            return {"send_direct": False, "result": self.calendar.search(query)}
        
        # Get top processes
        elif action == "get_top_processes":
            limit = parameters.get("limit", 5)
            return {"send_direct": False, "result": get_top_processes(limit=limit)}
        
        # Get latest news
        elif action == "get_news":
            latest = self.news_monitor.get_latest_video_transcript()
            if latest:
                print(f"\nLatest Video: {latest['title']}")
                print(f"Published: {latest['published_at']}")
                print("\nTranscript excerpt:")
                print(latest['transcript'][:500] + "...")
                
            summary = self.news_monitor.summarize_latest_video(self.client)
            return {"send_direct": True, "result": summary}
        
        else:
            return {"send_direct": False, "result": "Action not recognized"}
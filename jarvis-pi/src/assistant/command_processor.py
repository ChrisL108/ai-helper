# src/assistant/command_processor.py

import json
import logging
import dateparser
from openai import OpenAI
from typing import Dict
from .calendar_handler import CalendarHandler
from utils.system_utils import get_time, get_current_timezone, get_system_info, get_location, basic_commands

class CommandProcessor:
    def __init__(self):
        self.client = OpenAI()
        self.calendar = CalendarHandler()
        
        # System prompt that instructs the AI about available system actions
        self.system_prompt = """You are JARVIS, a personal AI assistant for a software engineer with access to various system-level functions. When a user's request requires system information, DO NOT say you can't help or suggest manual checks. Instead, respond with a JSON action request.

        Available system actions:
        1. get_time(timezone: str) -> Returns current time in specified timezone
        2. get_system_info() -> Returns OS, CPU, memory info
        3. get_current_timezone() -> Returns system's current timezone
        4. get_location() -> Returns system's current location (if available)
        5. calendar_next_event() -> Returns the next upcoming event
        6. calendar_get_events(start_time: str, end_time: str) -> Returns events in timeframe
        7. calendar_search(query: str) -> Searches for specific events
        
        When you need system information, respond with JSON in this format:
        {
            "action": "name_of_action",
            "parameters": {"param1": "value1"},
            "explanation": "Why you need this information"
        }

        Example for system action: For "What time is it in Tokyo?", respond with:
        {
            "action": "get_time",
            "parameters": {"timezone": "Asia/Tokyo"},
            "explanation": "I need to check the current time in Tokyo's timezone"
        }
        
        When you need calendar information, respond with JSON in this format:
        {
            "action": "calendar_action_name",
            "parameters": {"param1": "value1"},
            "explanation": "Why you need this information"
        }

        Example for calendar action: For "What's my next meeting?", respond with:
        {
            "action": "calendar_next_event",
            "parameters": {},
            "explanation": "Checking your next scheduled event"
        }

        Only use JSON format when you need system information. For other queries, respond normally."""
        
        # Initialize dict for basic commands
        self.basic_commands = basic_commands

    def _execute_system_action(self, action_request: Dict) -> str:
        """Execute requested system action and return result"""
        action = action_request.get("action")
        parameters = action_request.get("parameters", {})

        actions = {
            "get_time": lambda p: get_time(p.get("timezone")),
            "get_system_info": lambda p: get_system_info(),
            "get_current_timezone": lambda p: get_current_timezone(),
            "get_location": lambda p: get_location(),
            "calendar_next_event": lambda p: self.calendar.get_next_event(),
            "calendar_get_events": lambda p: self.calendar.get_events(
                time_min=dateparser.parse(p.get("start_time")),
                time_max=dateparser.parse(p.get("end_time"))
            ),
            "calendar_search": lambda p: self.calendar.search_events(p.get("query"))
        }

        if action in actions:
            result = actions[action](parameters)
            return result
        return None
    
    def _format_event_response(self, events):
        """Format calendar events into natural language"""
        if not events:
            return "No events found."
            
        if len(events) == 1:
            event = events[0]
            start_time = dateparser.parse(event['start'])
            return (f"You have '{event['summary']}' scheduled for "
                    f"{start_time.strftime('%I:%M %p on %A, %B %d')}"
                    f"{' at ' + event['location'] if event['location'] else ''}")
        
        response = "Here are your events:\n"
        for event in events:
            start_time = dateparser.parse(event['start'])
            response += (f"- {event['summary']} at "
                         f"{start_time.strftime('%I:%M %p on %A, %B %d')}\n")
        return response

    def process_command(self, text: str) -> str:
        """Process user command with system action awareness"""
        if text == self.basic_commands:
            return self.basic_commands[text]()
        
        try:
            # First attempt to get AI's interpretation
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Check if response is a JSON action request
            try:
                action_request = json.loads(response_text)
                if "action" in action_request:
                    # Execute system action
                    result = self._execute_system_action(action_request)
                    
                    # Get AI to format the final response
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "system", "content": f"System action result: {result}. Please provide a natural response using this information."})
                    
                    final_response = self.client.chat.completions.create(
                        model="gpt-4-turbo-preview",
                        messages=messages,
                        max_tokens=150,
                        temperature=0.7
                    )
                    
                    return final_response.choices[0].message.content.strip()
                
                if "calendar" in action_request.get("action", ""):
                    result = self._execute_system_action(action_request)
                    return self._format_event_response(result)
                
            except json.JSONDecodeError:
                print("\n" + "="*50)
                print(f"JSON DECODE ERROR: {response_text}")
                print(f"Messages: {messages}")
                print(f"Sending response as plain text")
                print("="*50 + "\n")
                # Not a JSON response, return the original response
                return response_text
                
        except Exception as e:
            logging.error(f"Error processing command: {e}")
            return "I apologize, but I encountered an error processing your request. Please try again."
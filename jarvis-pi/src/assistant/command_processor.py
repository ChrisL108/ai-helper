# src/assistant/command_processor.py

from openai import OpenAI
from datetime import datetime
import pytz
import json
import logging
import platform
import psutil
import os
from typing import Dict, Any

class CommandProcessor:
    def __init__(self):
        self.client = OpenAI()
        
        # System prompt that instructs the AI about available system actions
        self.system_prompt = """You are JARVIS, a personal AI assistant for a software engineer with access to various system-level functions. When a user's request requires system information, DO NOT say you can't help or suggest manual checks. Instead, respond with a JSON action request.

        Available system actions:
        1. get_time(timezone: str) -> Returns current time in specified timezone
        2. get_system_info() -> Returns OS, CPU, memory info
        3. get_current_timezone() -> Returns system's current timezone
        4. get_location() -> Returns system's current location (if available)
        
        When you need system information, respond with JSON in this format:
        {
            "action": "name_of_action",
            "parameters": {"param1": "value1"},
            "explanation": "Why you need this information"
        }

        Example: For "What time is it in Tokyo?", respond with:
        {
            "action": "get_time",
            "parameters": {"timezone": "Asia/Tokyo"},
            "explanation": "I need to check the current time in Tokyo's timezone"
        }

        Only use JSON format when you need system information. For other queries, respond normally."""
        
        # Initialize dict for basic commands
        self.basic_commands = {
            "time": lambda: self._get_time(self._get_current_timezone()),
            "date": lambda: datetime.now().strftime("%Y-%m-%d"),
            "hello": lambda: "Hello, how can I assist you today?",
            "goodbye": lambda: "Goodbye! Have a great day.",
            "exit": lambda: "Shutting down.",
            "quit": lambda: "Shutting it down."
        }

    def _get_time(self, timezone: str) -> str:
        """Get current time in specified timezone"""
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            return current_time.strftime("%I:%M %p %Z")
        except Exception as e:
            logging.error(f"Error getting time: {e}")
            return None

    def _get_current_timezone(self) -> str:
        """Get system's current timezone"""
        return str(datetime.now().astimezone().tzinfo)

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            "os": platform.system(),
            "version": platform.version(),
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent
        }

    def _get_location(self) -> Dict[str, Any]:
        """
        Get system location
        -- Not sure if this is a reliable approach
        """
        return {"timezone": self._get_current_timezone()}

    def _execute_system_action(self, action_request: Dict) -> str:
        """Execute requested system action and return result"""
        action = action_request.get("action")
        parameters = action_request.get("parameters", {})

        actions = {
            "get_time": lambda p: self._get_time(p.get("timezone")),
            "get_system_info": lambda p: self._get_system_info(),
            "get_current_timezone": lambda p: self._get_current_timezone(),
            "get_location": lambda p: self._get_location()
        }

        if action in actions:
            result = actions[action](parameters)
            return result
        return None

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
                
            except json.JSONDecodeError:
                # Not a JSON response, return the original response
                return response_text
                
        except Exception as e:
            logging.error(f"Error processing command: {e}")
            return "I apologize, but I encountered an error processing your request. Please try again."
# src/assistant/command_processor.py

import json
import logging
from openai import OpenAI
from anthropic import Anthropic
from typing import Dict, List, Tuple
from .calendar_handler import CalendarHandler
from utils.system_utils import get_time, _get_current_timezone, get_system_info, get_location, get_top_processes, basic_commands
import re
import time
from .news.youtube_channel_monitor import YouTubeChannelMonitor

class CommandProcessor:
    def __init__(self, llm_provider="openai"):
        self.llm_provider = llm_provider
        if llm_provider == "openai":
            self.client = OpenAI()
            self.model = "gpt-4-turbo-preview"
        else:
            self.client = Anthropic()
            self.model = "claude-3-sonnet-20240229"
        
        self.calendar = CalendarHandler()
        self.basic_commands = basic_commands
        self.news_monitor = YouTubeChannelMonitor()

        self.system_prompt = """You are JARVIS, a personal AI assistant for a software engineer with access to various system-level functions. When a user's request requires system information, respond with a JSON action request.

        Note: If obtaining certain information (like timezone) is a precursor to another action (like getting the current time), include all relevant data in your response to prevent extra back and forth requests.

        Important: When an action is needed, respond with JSON. For example, if the user asks "how's my system running", respond with:
        {
            "action": "get_system_info",
            "parameters": {},
            "explanation": "To provide an overview of your system's current status, including operating system, CPU, and memory usage."
        }
        
        Available system actions:
        1. get_time() -> Returns current time, according to their system
        2. get_system_info() -> Returns OS, CPU, memory info
        4. get_location() -> Returns system's current location (if available)
        5. calendar_next_event() -> Returns the next upcoming event
        6. calendar_get_events(start_time: str, end_time: str) -> Returns events in timeframe
        7. calendar_search(query: str) -> Searches for specific events
        8. get_top_processes(limit: int) -> Returns top processes by CPU and memory usage
        9. get_news() -> Returns transcript of specific news for you to summarize
        
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

        Only use JSON format when you need system information. For other queries, respond normally.
        When responding normally, ensure responses are as concise as possible. For example, instead of saying "The current time in your timezone (America/Bahia_Banderas) is 08:00 PM CST.", simply say "It's 8 PM".
        """


    def _format_messages_for_openai(self, text: str, context: List[Tuple[str, str, str]]) -> List[Dict]:
        """Format messages for OpenAI API"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add context from previous interactions
        for user_message, assistant_response, _ in context:
            messages.append({"role": "user", "content": user_message})
            messages.append({"role": "assistant", "content": assistant_response})
        
        # Add current message
        messages.append({"role": "user", "content": text})
        print(f"👀 OpenAI messages:")
        for message in messages:
            if message['role'] != "system":
                print(f"➡️ {message['role']}: {message['content']}")
            else:
                print(f"🤖 SYSTEM PROMPT LENGTH: {len(message['content'])} characters")
        return messages

    def _format_messages_for_claude(self, text: str, context: List[Tuple[str, str, str]]) -> List[Dict]:
        """Format messages for Claude API"""
        # Build conversation history
        conversation = f"System: {self.system_prompt}\n\n"
        
        # Add context
        for user_message, assistant_response, _ in context:
            conversation += f"Human: {user_message}\n\n"
            conversation += f"Assistant: {assistant_response}\n\n"
        
        # Add current message
        conversation += f"Human: {text}\n\nAssistant:"
        
        return [{"role": "user", "content": conversation}]

    def _get_ai_response(self, messages: List[Dict], max_tokens: int = 150, temperature: float = 0.7) -> str:
        """Get completion from either AI provider"""
        try:
            if self.llm_provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                print(f"🔍 OpenAI response: {response.choices[0].message.content}")
                return response.choices[0].message.content
            else:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages
                )
                print(f"🔍 Claude response: {response.content[0].text}")
                return response.content[0].text
        except Exception as e:
            logging.error(f"Error getting completion: {str(e)}")
            raise

    def _execute_system_action(self, action_request: Dict) -> Dict[str, any]:
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
        
    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON content from a response with JSON code delimiters.
        Necessary because the LLM may return a JSON object as a string, but it may also return a JSON object within code delimiters.
        """
        try:
            # Regular expression to match JSON content within code delimiters
            json_pattern = r"```json\s*({.*?})\s*```"
            match = re.search(json_pattern, response_text, re.DOTALL)
            
            if match:
                print(f"🎃 JSON pattern match: {match.group(1)}")
                # Return the JSON content found between the delimiters
                return match.group(1)
            else:
                print("🔍🙅‍♂️ No JSON pattern match found")
                return response_text
        except Exception as e:
            logging.error(f"Error extracting JSON from response: {str(e)}")
            return response_text

    def process_command(self, text: str, context: List[Tuple[str, str, str]]) -> str:
        """Process user command with context awareness"""
        # TODO re-enable basic commands
        # if text.lower() in self.basic_commands:
        #     return self.basic_commands[text.lower()]()
        
        print(f"🔍 Processing command: {text}")
        try:
            # Format messages based on provider
            messages = (self._format_messages_for_openai(text, context) 
                       if self.llm_provider == "openai" 
                       else self._format_messages_for_claude(text, context))
            
            print(f"🔍 Getting AI response")
            # Get initial response
            response_text = self._get_ai_response(messages)
            
            print(f"🔍 Attempting to extract JSON from response")
            parsed_response_text = self._extract_json_from_response(response_text) if type(response_text) == str else response_text
            
            # Try to parse as JSON action request
            try:
                print(f"🔍 Attempting to parse JSON action request")
                action_request = json.loads(parsed_response_text)
                print(f"🔍 Action request: {action_request}")
                if "action" in action_request:
                    print(f"🔍 Found action request: '{action_request['action']}'")
                    # Execute system action
                    action_result = self._execute_system_action(action_request)
                    result = action_result.get("result")
                    send_direct = action_result.get("send_direct")
                    
                    print(f"🔍 Action result: {result}, Direct Response?: {send_direct}")
                    
                    if send_direct:
                        # NOTE: for some reason, w/o this delay the TTS is cutting off the beginning of the response
                        time.sleep(0.4)
                        return result
                    
                    # Add result to conversation
                    if self.llm_provider == "openai":
                        messages.append({"role": "assistant", "content": response_text})
                        messages.append({
                            "role": "system",
                            "content": f"Action result: {result}. Provide a natural language response."
                        })
                    else:
                        messages = self._format_messages_for_claude(
                            text,
                            context + [(text, f"Action completed. Result: {result}", "")]
                        )
                    
                    # TODO some cases, we can return the result directly instead of asking the LLM
                    # Get final natural language response
                    return self._get_ai_response(messages)
                
            except json.JSONDecodeError:
                print("↘️ Not a JSON response, returning as is")
                # Not a JSON response, return as is
                return response_text
                
        except Exception as e:
            logging.error(f"Error processing command: {str(e)}")
            return "Didn't catch that."
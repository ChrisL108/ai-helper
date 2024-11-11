# src/assistant/command_processor.py

import json
import logging
from openai import OpenAI
from typing import Dict, List, Tuple
import time
from assistant.tooling.tooling_manager import ToolingManager

MODEL = "gpt-4-turbo-preview"
# MODEL = "gpt-4o-mini" # Not as good at returning action requests

class CommandProcessor:
    def __init__(self):
        self.client = OpenAI()
        self.tooling_manager = ToolingManager()

    def _get_ai_response(self, messages: List[Dict], max_tokens: int = 150, temperature: float = 0.7) -> str:
        """Get completion from AI provider"""
        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            print(f"🔍 OpenAI response: {response.choices[0].message.content}")
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error getting completion: {str(e)}")
            raise
        

    def process_command(self, text: str, context: List[Tuple[str, str, str]]) -> str:
        """Process user command with context awareness"""
        print(f"🔍 Processing command: {text}")

        try:
            # Format messages based on provider
            messages = self.tooling_manager.format_messages_for_openai(text, context)
            
            print(f"🔍 Getting AI response")
            # Get initial response
            response_text = self._get_ai_response(messages)
            
            print(f"🔍 Attempting to extract JSON from response")
            json_or_str_response = self.tooling_manager.extract_json_from_str(response_text)
            
            # Try to parse as JSON action request
            try:
                print(f"🔍 Attempting to parse JSON action request")
                action_request = json.loads(json_or_str_response)
                print(f"🔍 Action request: {action_request}")
                
                if "action" in action_request:
                    print(f"🔍 Found action request: '{action_request['action']}'")
                    
                    # Execute system action
                    action_result = self.tooling_manager.execute_system_action(action_request)
                    result = action_result.get("result")
                    send_direct = action_result.get("send_direct")
                    
                    print(f"🔍 Action result: {result}, Direct Response?: {send_direct}")
                    
                    if send_direct:
                        # TODO - something seems to be cutting off the beginning of the response
                        # time.sleep(0.4)
                        return result
                    
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({
                        "role": "system",
                        "content": f"Action result: {result}. Provide a natural language response."
                    })
                    
                    # Get final AI response
                    return self._get_ai_response(messages)
                
            except json.JSONDecodeError:
                print("↘️ Not a JSON response, returning as is")
                # Not a JSON response, return as is
                return response_text
                
        except Exception as e:
            logging.error(f"Error processing command: {str(e)}")
            return "Didn't catch that."
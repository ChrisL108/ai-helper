import logging
from typing import List, Tuple, Dict
import re
from assistant.prompts import SYSTEM_PROMPT
    
def format_messages_for_openai(text: str, context: List[Tuple[str, str, str]]) -> List[Dict]:
    """Format messages for OpenAI API"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
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

def format_messages_for_claude(text: str, context: List[Tuple[str, str, str]]) -> List[Dict]:
    """Format messages for Claude API"""
    # Build conversation history
    conversation = f"System: {SYSTEM_PROMPT}\n\n"
    
    # Add context
    for user_message, assistant_response, _ in context:
        conversation += f"Human: {user_message}\n\n"
        conversation += f"Assistant: {assistant_response}\n\n"
    
    # Add current message
    conversation += f"Human: {text}\n\nAssistant:"
    
    return [{"role": "user", "content": conversation}]

def extract_json_from_str(response_text: str) -> str:
    """
    Extract JSON content from a response with JSON code delimiters.
    NOTE: LLM sometimes returns a JSON object in a str w/ code delimiters, maybe we can fix in system prompt?
    """
    if type(response_text) != str:
        return response_text
    
    try:
        # Regular expression to match JSON content within code delimiters
        json_pattern = r"```json\s*({.*?})\s*```"
        match = re.search(json_pattern, response_text, re.DOTALL)
        
        if match:
            print(f"🎃 JSON pattern match: {match.group(1)}")
            # Return the JSON content found between the delimiters
            return match.group(1)
        else:
            print("🔍 No JSON pattern match found")
            return response_text
    except Exception as e:
        logging.error(f"Error extracting JSON from response: {str(e)}")
        return response_text
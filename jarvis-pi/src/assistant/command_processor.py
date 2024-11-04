from openai import OpenAI
from datetime import datetime
import logging

class CommandProcessor:
    def __init__(self):
        self.client = OpenAI()
# System prompt for the AI assistant
        self.system_prompt = """You are JARVIS, a personal AI assistant for a software engineer. You have these key characteristics:
        
        1. Technical Expertise: You're well-versed in programming languages, development tools, and software engineering concepts
        2. Efficiency: You provide concise, practical answers focused on technical solutions
        3. Proactive: You anticipate potential issues and suggest best practices
        4. Context-Aware: You understand software development workflows and common development tasks
        5. Personality: You're professional but have a subtle wit, similar to the JARVIS from Iron Man
        
        Keep responses concise and focused on actionable information. If you need to show code, keep it brief unless specifically asked for more detail.
        
        Current user context: You're running on their local machine as a voice assistant, so avoid suggesting clicks or visual references."""

        # Initialize dict for basic commands
        self.basic_commands = {
            "time": self._get_time,
            "date": self._get_date,
            "hello": self._greeting,
            "goodbye": self._goodbye,
            "exit": self._goodbye,
            "quit": self._goodbye
        }
        
    def _get_time(self):
        return f"It's {datetime.now().strftime('%I:%M %p')}"
        
    def _get_date(self):
        return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}"
        
    def _greeting(self):
        return "Hello! How can I assist you with your development tasks today?"
        
    def _goodbye(self):
        return "Goodbye! Let me know if you need any further assistance."
    
    def process_command(self, command):
        try:
            command = command.lower()
            if command in self.basic_commands:
                return self.basic_commands[command]()
        
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": command}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200,
                temperature=0.7,
                presence_penalty=0.5,
            )

            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error processing command: {e}")
            return "I'm sorry, I'm having trouble processing that command. Please try again."

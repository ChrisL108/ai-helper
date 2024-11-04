# src/main.py

import logging
from assistant.voice_recognition import VoiceRecognizer
from assistant.text_to_speech import TextToSpeech
from assistant.command_processor import CommandProcessor
import signal
import sys
import time

class Jarvis:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.voice_recognizer = VoiceRecognizer()
        self.tts = TextToSpeech()
        self.is_running = True
        self.command_processor = CommandProcessor()
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.cleanup)
        
    def run(self):
        """Main loop of the assistant"""
        self.tts.speak("Hello, I'm Jarvis. How can I help you?", voice="nova")
        
        while self.is_running:
            try:
                # Wait for any ongoing speech to complete
                while self.tts.is_speaking:
                    time.sleep(0.1)
                
                # Listen for command
                text = self.voice_recognizer.listen()
                
                if text:
                    # Process command and get response
                    response = self.command_processor.process_command(text)
                    
                    # Speak response
                    print(f"Response: {response}")
                    try:    
                        self.tts.speak(response, voice="nova")
                    except Exception as e:
                        logging.error(f"Error speaking response: {e}")
                        self.tts.speak("I can't talk in code sir.", voice="nova")
                    
                    time.sleep(1)
                    # Check for exit command
                    if any(word in response.lower() for word in ["goodbye", "exit", "quit"]):
                        self.cleanup()
                        
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
                
    def cleanup(self, signum=None, frame=None):
        """Cleanup resources and exit gracefully"""
        print("\nShutting down...")
        self.is_running = False
        self.tts.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    assistant = Jarvis()
    assistant.run()
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
        self.command_processor = CommandProcessor()
        self.voice_recognizer = VoiceRecognizer()
        self.tts = TextToSpeech()
        self.is_running = True

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.cleanup)
        
    def speak_and_wait(self, text, voice="onyx"):
        self.tts.speak(text, voice=voice)
        self.tts.wait_until_done()
        # Add extra delay after speaking to avoid echo
        time.sleep(1.0)
        
    def run(self):
        """Main loop of the assistant"""
        self.speak_and_wait("Hello, I'm Jarvis. How can I help you?")
        
        while self.is_running:
            try:
                if not self.tts.is_speaking:
                    # # Wait for any ongoing speech to complete
                    # while self.tts.is_speaking:
                    #     time.sleep(0.1)
                    
                    # Listen for command
                    text = self.voice_recognizer.listen()
                    
                    if text:
                        # Process command and get response
                        response = self.command_processor.process_command(text)
                        
                        # Speak response
                        print(f"User: {text}")
                        print(f"JARVIS: {response}")
                        self.speak_and_wait(response)
                        
                        # Check for exit command
                        if any(word in response.lower() for word in ["goodbye", "exit", "quit"]):
                            self.cleanup()
                else:
                    time.sleep(0.1)
                            
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
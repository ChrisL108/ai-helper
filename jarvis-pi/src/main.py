import logging
import signal
import sys
import time
import threading
from gui.ui_handler import AssistantUI
from assistant.text_to_speech import TextToSpeech
from assistant.voice_recognition import VoiceRecognizer
from assistant.command_processor import CommandProcessor
# from assistant.memory.integrated_memory_system import IntegratedMemorySystem
from assistant.memory.basic_memory import BasicMemory

class Jarvis:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.command_processor = CommandProcessor()
        self.voice_recognizer = VoiceRecognizer()
        self.tts = TextToSpeech()
        self.ui = AssistantUI()
        self.is_running = True
        self.voice_thread = None
        
        # Callback to stop the assistant's active TTS
        self.ui.stop_callback = self.stop
        self.ui.exit_callback = self.cleanup

        # Initialize memory systems
        # self.memory_system = IntegratedMemorySystem()
        self.memory_system = BasicMemory()

        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.cleanup)
        
    def speak_and_wait(self, text, voice="onyx"):
        self.ui.set_state("speaking")
        self.ui.update_transcript(text)
        self.tts.speak(text, voice=voice)
        self.tts.wait_until_done()
        # Add extra delay after speaking to avoid echo
        time.sleep(1.0)
        self.ui.set_state("idle")

    def run(self):
        """Main loop of the assistant"""
        
        # Schedule the main loop task before starting the Tkinter main loop
        self.ui.r.after(50, self.main_loop)
        
        # Start UI in the main thread
        self.ui.run()  # This starts the Tkinter main loop
        
    def stop(self):
        """Stop the assistant and say a message."""
        # Interrupt the TTS if it's speaking
        if self.tts.is_speaking:
            self.tts.stop()
            self.speak_and_wait("Okay, I'll stop")
        else:
            self.speak_and_wait("I wasn't talking, chill")
        # self.is_running = False
        
    def main_loop(self):
        """Main loop task scheduled with Tkinter's `after` method"""
        if self.is_running:
            try:
                if not self.tts.is_speaking:
                    self.ui.set_state("listening")
                    
                    # Start listening in a separate thread
                    if self.voice_thread is None or not self.voice_thread.is_alive():
                        self.voice_thread = threading.Thread(target=self.listen_and_process)
                        self.voice_thread.start()
                        
                else:
                    self.ui.set_state("idle")
                            
            except Exception as e:
                logging.error(f"Error in main loop: {e}")
            
            # Reschedule the main loop task
            self.ui.r.after(100, self.main_loop)
                
    def listen_and_process(self):
        """Listen for command and process it"""
        text = self.voice_recognizer.listen()

        if text:
            # Update UI with user's text
            self.ui.update_transcript(text, is_user=True)
            self.ui.set_state("processing")
            
            context = self.memory_system.get_recent_interactions(limit=5)
            print(f"👀 Context: {context}")
            
            # Process command and get response
            response = self.command_processor.process_command(text, context)
            
            # Store interaction in memory system
            self.memory_system.add_interaction(
                user_id="1", # TODO: any use for multiple user ids?
                user_message=text,
                assistant_response=response
            )
            
            # Speak response
            print(f"User: {text}")
            print(f"JARVIS: {response}")
            self.speak_and_wait(response)
            
            # Check for exit command
            if any(word in response.lower() for word in ["goodbye", "exit", "quit"]):
                self.cleanup()
        else:
            self.ui.set_state("idle")

    def cleanup(self, signum=None, frame=None):
        """Cleanup resources and exit gracefully"""
        print("\nShutting down JARVIS...")
        self.is_running = False
        self.tts.cleanup()
        self.ui.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    assistant = Jarvis()
    assistant.run()
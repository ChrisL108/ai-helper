# src/assistant/text_to_speech.py

import logging
from openai import OpenAI
import io
import pygame
import time
import threading
from queue import Queue

class TextToSpeech:
    def __init__(self):
        logging.debug("Initializing TextToSpeech class.")
        self.client = OpenAI()
        # Initialize pygame mixer
        pygame.mixer.init()
        self.audio_queue = Queue()
        self.is_speaking = False
        self._setup_playback_thread()
    
    def _setup_playback_thread(self):
        """Initialize and start the playback thread"""
        logging.debug("Setting up playback thread.")
        self.playback_thread = threading.Thread(target=self._process_audio_queue, daemon=True)
        self.playback_thread.start()
        
    def stop(self):
        """Stop the TTS"""
        logging.debug("Stopping text-to-speech playback.")
        pygame.mixer.music.stop()
        self.is_speaking = False
        
    def speak(self, text, voice="onyx"):
        """
        Convert text to speech using OpenAI's API and play it immediately
        voice options: alloy, echo, fable, onyx, nova, shimmer
        """
        logging.debug(f"Received text to speak: {text} with voice: {voice}")
        try:
            # Generate speech using OpenAI
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            logging.debug("Speech generated successfully.")
            
            # Get the audio data in memory
            audio_data = io.BytesIO()
            for chunk in response.iter_bytes(chunk_size=4096):
                audio_data.write(chunk)
            audio_data.seek(0)
            logging.debug("Audio data written to memory.")
            
            # Add to playback queue
            self.audio_queue.put(audio_data)
            logging.debug("Audio data added to queue.")
            
            # Wait until speech is complete if needed
            while self.is_speaking:
                logging.debug("Waiting for current speech to complete.")
                time.sleep(0.1)
            
        except Exception as e:
            logging.error(f"Error in text-to-speech: {e}")
            self.is_speaking = False

    def _process_audio_queue(self):
        """Process audio queue in a separate thread"""
        logging.debug("Starting audio queue processing thread.")
        while True:
            try:
                # Get audio data from queue
                audio_data = self.audio_queue.get()
                logging.debug("Retrieved audio data from queue.")
                self.is_speaking = True
                
                # Play the audio
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()
                logging.debug("Audio playback started.")
                
                # Wait for audio to finish
                while pygame.mixer.music.get_busy():
                    logging.debug("Audio is playing...")
                    time.sleep(0.2)
                
                self.is_speaking = False
                self.audio_queue.task_done()
                logging.debug("Audio playback finished.")
                
            except Exception as e:
                logging.error(f"Error in audio playback: {e}")
                self.is_speaking = False

    def wait_until_done(self):
        """Wait until all speech is complete"""
        logging.debug("Waiting for all speech to complete.")
        while self.is_speaking or not self.audio_queue.empty():
            time.sleep(0.1)
            
    def cleanup(self):
        """Cleanup pygame resources"""
        logging.debug("Cleaning up pygame resources.")
        pygame.mixer.quit()
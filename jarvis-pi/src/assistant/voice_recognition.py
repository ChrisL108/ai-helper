import speech_recognition as sr
from datetime import datetime
import logging

class VoiceRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            logging.info("Adjusting for ambient noise. Please speak now.")
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.energy_threshold = 300

        logging.info("Jarvis initialized.")
        
    def listen(self):
        """Listen for a single phrase and return the text."""
        text = ""
        
        try:
            with self.microphone as source:
                print("Listening...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
            print("Recognizing...")
            text = self.recognizer.recognize_google(audio)
            print("You said: ", text)
            
        except sr.WaitTimeoutError:
            print("Timeout - No speech detected")
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
        except Exception as e:
            print(f"Error: {e}")

        return text.lower() if text else ""

    def is_wake_word(self, text, wake_word="jarvis"):
        return wake_word.lower() in text.lower()

    def process_command(self, text):
        """Command processing."""
        text = text.lower()
        
        if "time" in text:
            return f"The time is {datetime.now().strftime('%I:%M %p')}"
        elif "kayden" in text or "caden" in text:
            return "Hello, Kayden!"
        elif "hello" in text:
            return "Hello, how can I assist you today Mr. Clac?"
        elif "exit" in text or "quit" in text or "goodbye" in text:
            return "Goodbye Mr. Clac!"
        elif "weather" in text:
            return self.get_weather() if self.get_weather() else "I couldn't fetch the weather data."
        elif self.is_wake_word(text):
            return "What up dog?"
        else:
            return "i am so dumb so please be dumb for me"
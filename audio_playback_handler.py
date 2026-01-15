import os
import sys
import time
import logging
import subprocess
import ctypes
from ctypes import wintypes

class AudioPlaybackHandler:
    def __init__(self):
        self.window_configured = False

    def display_text(self, text):
        """Logs the text being spoken (no window)."""
        logging.info(f"AUDIO_TEXT: {text}")

    def play_audio(self, file_path):
        """Plays audio using simpleaudio (head-less)."""
        if not os.path.exists(file_path):
            logging.error(f"Audio file missing: {file_path}")
            return
            
        try:
            logging.info(f"Playing via simpleaudio: {file_path}")
            import simpleaudio as sa
            wave_obj = sa.WaveObject.from_wave_file(file_path)
            play_obj = wave_obj.play()
            play_obj.wait_done()
            logging.info("Playback finished.")
            
        except Exception as e:
            logging.error(f"Playback error: {e}")
            # Fallback to winsound
            try:
                import winsound
                winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
            except:
                pass

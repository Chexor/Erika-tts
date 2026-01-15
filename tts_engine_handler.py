import sys
import os
import subprocess
import logging
import tempfile
import requests

class TTSEngineHandler:
    def __init__(self, venv_python_path):
        self.venv_python = venv_python_path
        self.server_url = "http://localhost:5050"
        
    def generate_speech(self, text, config, base_dir):
        """
        Generates speech via the VibeVoice TTS Server.
        """
        engine = config.get("engine", "vibevoice")
        voice = config.get("voice", "")

        # Determine language based on config
        # Default to 'en' unless Dutch is explicitly requested or detected
        lang = "en"
        # Flags for Dutch: nl engine, nd/nl voice, Dutch in voice, vibevoice in engine
        if "nl" in engine or "nd" in voice or "nl-" in voice or "Dutch" in voice:
            lang = "nl"
        
        logging.info(f"Routing to VibeVoice: lang={lang}, voice={voice}")
        
        output_path = self._generate_via_server(lang, text, voice)
        
        if output_path:
            return output_path
        
        logging.error("Server generation failed.")
        return None

    def _generate_via_server(self, lang, text, voice=None):
        try:
            endpoint = f"{self.server_url}/generate"
            payload = {
                "text": text, 
                "lang": lang,
                "voice": voice # Let server override if provided
            }
                
            logging.info(f"Requesting audio from Kokoro server ({lang}/{voice}): {text[:30]}...")
            response = requests.post(endpoint, json=payload, timeout=30)
            
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(response.content)
                    return f.name
            else:
                logging.error(f"Server returned error: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Server connection failed: {e}")
            return None

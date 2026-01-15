import json
import os
import logging

class TTSInterpreter:
    def __init__(self, config_path="tts_config.json"):
        self.config = self._load_config(config_path)

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            # Return resilient default
            return {
                "default_language": "en",
                "languages": {
                    "en": {"engine": "pocket_tts", "voice": "azelma"}
                }
            }

    def process(self, text):
        """
        Determines the language/engine configuration for the given text.
        Returns: (config_dict, clean_text)
        """
        try:
            from langdetect import detect, DetectorFactory
            DetectorFactory.seed = 0 # Deterministic
            lang_code = detect(text)
            if lang_code != "nl":
                lang_code = "en"
        except Exception:
            lang_code = self.config.get("default_language", "en")
            
        lang_config = self.config["languages"].get(lang_code, self.config["languages"]["en"])
        
        return lang_config, text

import argparse
import sys
import os
import logging
import traceback

# Import new modules
from tts_interpreter import TTSInterpreter
from tts_engine_handler import TTSEngineHandler
from audio_playback_handler import AudioPlaybackHandler

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")

# Setup logging
logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, "worker_debug.log"),
    level=logging.INFO,
    format='%(asctime)s - WORKER - %(levelname)s - %(message)s',
    force=True
)

def perform_speech(text, voice, input_file=None):
    try:
        # Initialize Handlers
        interpreter = TTSInterpreter(os.path.join(SCRIPT_DIR, "tts_config.json"))
        engine_handler = TTSEngineHandler(VENV_PYTHON)
        playback_handler = AudioPlaybackHandler()

        # Step 1: Interpret Input
        # Note: If input_file is provided, we might skip interpretation or use it for text display
        lang_config, clean_text = interpreter.process(text)
        
        # Override voice if provided in args and not default
        # But if we want the interpreter to decide, we should prioritize config?
        # For now, let's respect the CLI arg if it's explicitly set to something standard
        # But the interpreter returns the *config block* for the language.
        # We can merge them.
        
        logging.info(f"Interpreted Language Config: {lang_config}")
        
        # Step 2: Generate Audio (if no input file)
        audio_path = input_file
        if not audio_path:
            audio_path = engine_handler.generate_speech(clean_text, lang_config, SCRIPT_DIR)
        
        if not audio_path:
            logging.error("Failed to obtain audio path.")
            return

        # Step 3: Playback & Display
        # Display the text provided (or defaults)
        playback_handler.display_text(clean_text)
        
        # Play the audio
        playback_handler.play_audio(audio_path)

    except Exception as e:
        logging.critical(f"Pipeline failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--text", default="Playing audio...")
        parser.add_argument("--voice", default="default") 
        parser.add_argument("--input-file", default=None)
        args = parser.parse_args()

        if args.input_file is None and args.text == "Playing audio...":
            # This check is a bit loose, but matches previous user logic
            # If called with no args, it might default here.
            # But the server always sends --text
            pass

        perform_speech(text=args.text, voice=args.voice, input_file=args.input_file)
        
    except Exception as e:
        sys.stderr.write(f"Worker crashed: {e}\n")
        traceback.print_exc()
        sys.exit(1)

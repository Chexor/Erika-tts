import subprocess
import sys
import os
import datetime
import glob
import time
import yaml
import simpleaudio as sa

SETTINGS_FILE = "erika_settings.yaml"
ALLOWED_VOICES = ['alba', 'marius', 'javert', 'jean', 'fantine', 'cosette', 'eponine', 'azelma']
SUPPORTED_LANGUAGES = ['en', 'nl', 'auto']


def detect_language(text):
    """Detect if text is English or Dutch using langdetect."""
    try:
        from langdetect import detect, DetectorFactory
        # Make detection deterministic
        DetectorFactory.seed = 0

        # langdetect is unreliable for short texts, require minimum length
        if len(text.split()) < 4:
            print("(Text too short for reliable detection, defaulting to English)")
            return 'en'

        lang = detect(text)
        # Map detected language to our supported set
        if lang == 'nl':
            return 'nl'
        else:
            # Default to English for any non-Dutch language
            return 'en'
    except Exception as e:
        print(f"Language detection failed: {e}. Defaulting to English.")
        return 'en'

def load_settings(script_dir):
    settings_path = os.path.join(script_dir, SETTINGS_FILE)
    default_settings = {
        "default_voice": "azelma",
        "output_folder_name": "erika_tts_output",
        "max_audio_files": 5,
        "default_language": "auto",
        "generation_settings": {
            "temperature": 0.7,
            "lsd_decode_steps": 1,
            "noise_clamp": None,
            "eos_threshold": -4.0,
            "frames_after_eos": None,
            "device": "cpu",
        },
        "parkiet_settings": {
            "device": "cuda",
            "max_new_tokens": 3072,
            "guidance_scale": 3.0,
            "temperature": 1.8,
            "top_p": 0.90,
            "top_k": 50,
        }
    }

    if not os.path.exists(settings_path):
        print(f"Warning: Settings file '{SETTINGS_FILE}' not found. Using default settings.")
        return default_settings

    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            user_settings = yaml.safe_load(f)
        
        # Merge with defaults to ensure all keys are present
        settings = default_settings.copy()
        if user_settings: # Check if user_settings is not None/empty
            # Recursively merge generation_settings
            if "generation_settings" in user_settings and user_settings["generation_settings"] is not None:
                settings["generation_settings"].update(user_settings["generation_settings"])
            # Recursively merge parkiet_settings
            if "parkiet_settings" in user_settings and user_settings["parkiet_settings"] is not None:
                settings["parkiet_settings"].update(user_settings["parkiet_settings"])
            # Update top-level settings
            for key, value in user_settings.items():
                if key not in ("generation_settings", "parkiet_settings"):
                    settings[key] = value
        
        return settings
    except yaml.YAMLError as e:
        print(f"Error reading settings file '{SETTINGS_FILE}': {e}. Using default settings.")
        return default_settings
    except Exception as e:
        print(f"An unexpected error occurred while loading settings: {e}. Using default settings.")
        return default_settings

def ensure_output_folder_exists(script_dir, output_folder_name):
    output_path = os.path.join(script_dir, output_folder_name)
    os.makedirs(output_path, exist_ok=True)
    return output_path

def get_venv_python(script_dir):
    # Try venv312 first (Python 3.12 with better compatibility), then fall back to venv
    for venv_name in ["venv312", "venv"]:
        venv_path = os.path.join(script_dir, venv_name)
        python_exe = os.path.join(venv_path, "Scripts", "python.exe")
        if os.path.isdir(venv_path) and os.path.exists(python_exe):
            return python_exe

    print("Error: No virtual environment found.")
    print("Please ensure 'venv312' or 'venv' directory exists in the same location as this script.")
    sys.exit(1)

def clean_old_audio_files(output_dir, max_audio_files):
    audio_files = sorted(
        glob.glob(os.path.join(output_dir, "*.wav")),
        key=os.path.getmtime,
        reverse=True
    )
    if len(audio_files) > max_audio_files:
        for old_file in audio_files[max_audio_files:]:
            try:
                os.remove(old_file)
                print(f"Removed old audio file: {old_file}")
            except OSError as e:
                print(f"Error removing file {old_file}: {e}")


def generate_english(text_to_generate, settings, voice, full_output_path, script_dir):
    """Generate English speech using Pocket TTS."""
    python_exe = get_venv_python(script_dir)

    # Construct the pocket-tts command using python -m pocket_tts
    command_args = [
        python_exe, "-m", "pocket_tts", "generate",
        "--text", text_to_generate,
        "--output-path", full_output_path
    ]
    if voice:
        command_args.extend(["--voice", voice])

    # Add generation settings from the config file
    gen_settings = settings["generation_settings"]
    for param, value in gen_settings.items():
        if value is not None:
            # Convert snake_case to kebab-case for CLI arguments
            command_args.extend([f"--{param.replace('_', '-')}", str(value)])

    print(f"Engine: Pocket TTS (English)")
    print(f"Executing: {' '.join(command_args)}")

    result = subprocess.run(command_args, check=True, capture_output=True, text=True)
    if result.stderr:
        print(result.stderr)
    return os.path.exists(full_output_path)


def generate_dutch(text_to_generate, settings, full_output_path):
    """Generate Dutch speech using Parkiet."""
    import parkiet_engine

    if not parkiet_engine.is_available():
        print("Error: Parkiet dependencies not installed.")
        print("Please run: pip install transformers soundfile torch")
        return False

    print(f"Engine: Parkiet (Dutch)")
    return parkiet_engine.generate_dutch_speech(
        text_to_generate,
        full_output_path,
        settings.get("parkiet_settings", {})
    )


def erika_tts_generate(text_to_generate, settings, voice=None, custom_output_filename=None, language=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = ensure_output_folder_exists(script_dir, settings["output_folder_name"])

    # Determine language
    lang_setting = language if language else settings.get("default_language", "auto")
    if lang_setting == "auto":
        detected_lang = detect_language(text_to_generate)
        print(f"Auto-detected language: {detected_lang}")
    else:
        detected_lang = lang_setting

    # If voice is not provided by command line, use default from settings (only for English)
    actual_voice = voice if voice is not None else settings["default_voice"]

    # Voice validation logic (only applies to English/Pocket TTS)
    if detected_lang == "en":
        if not os.path.exists(actual_voice) and actual_voice not in ALLOWED_VOICES:
            print(f"Error: Invalid voice '{actual_voice}'.")
            print(f"Allowed voices are: {', '.join(ALLOWED_VOICES)} OR a valid path to a WAV file.")
            sys.exit(1)

    # Generate a unique filename if not provided
    if custom_output_filename:
        # Ensure it's a .wav file
        if not custom_output_filename.endswith(".wav"):
            custom_output_filename += ".wav"
        output_filename = custom_output_filename
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        lang_suffix = "nl" if detected_lang == "nl" else "en"
        output_filename = f"erika_output_{timestamp}_{lang_suffix}.wav"

    full_output_path = os.path.join(output_dir, output_filename)

    print(f"\n--- Generating TTS ---")
    print(f"Text: \"{text_to_generate}\"")
    print(f"Language: {detected_lang}")
    if detected_lang == "en":
        print(f"Voice: {actual_voice if actual_voice else 'Default (from settings)'}")
    print(f"Output: {full_output_path}")

    try:
        if detected_lang == "nl":
            success = generate_dutch(text_to_generate, settings, full_output_path)
        else:
            success = generate_english(text_to_generate, settings, actual_voice, full_output_path, script_dir)

        if success and os.path.exists(full_output_path):
            print(f"\nTTS generated successfully at {full_output_path}")
            clean_old_audio_files(output_dir, settings["max_audio_files"])
            # Play audio if not disabled
            if not os.environ.get("ERIKA_NO_PLAYBACK"):
                print("Playing audio...")
                try:
                    wave_obj = sa.WaveObject.from_wave_file(full_output_path)
                    play_obj = wave_obj.play()
                    play_obj.wait_done()
                except Exception as e:
                    print(f"Audio playback failed: {e}")
        else:
            print(f"\nError: Expected output file '{full_output_path}' was not created.")

    except subprocess.CalledProcessError as e:
        print(f"\nError generating TTS:")
        if e.stderr:
            print(e.stderr)
        print("\nPlease ensure 'pocket-tts' is installed in the virtual environment and the arguments are valid.")
    except FileNotFoundError:
        print(f"Error: Python executable not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    settings = load_settings(script_dir) # Load settings here

    # Remove the script name from arguments
    args = sys.argv[1:]

    text_to_generate = None
    voice = None # Initialize as None, will default to settings if not provided by CLI
    output_filename = None # User-specified output filename, not full path
    language = None # Language override: en, nl, or auto

    # Simple argument parsing
    i = 0
    while i < len(args):
        if args[i] == "--text":
            if i + 1 < len(args):
                text_to_generate = args[i+1]
                i += 1
        elif args[i] == "--voice":
            if i + 1 < len(args):
                voice = args[i+1]
                i += 1
        elif args[i] == "--output":
            if i + 1 < len(args):
                output_filename = args[i+1]
                i += 1
        elif args[i] == "--lang":
            if i + 1 < len(args):
                language = args[i+1].lower()
                if language not in SUPPORTED_LANGUAGES:
                    print(f"Error: Invalid language '{language}'. Supported: {', '.join(SUPPORTED_LANGUAGES)}")
                    sys.exit(1)
                i += 1
        else:
            # If --text was not used, assume the first positional argument is the text
            if text_to_generate is None:
                text_to_generate = args[i]
            else:
                print(f"Warning: Unrecognized argument or duplicate text value '{args[i]}'. Ignoring.")
        i += 1

    if text_to_generate is None:
        print("Usage: python Erika-tts.py --text \"Your text here\" [--voice voice_name] [--output filename.wav] [--lang en|nl|auto]")
        print(f"\nSettings (from {SETTINGS_FILE}):")
        print(f"  Default voice: '{settings['default_voice']}'")
        print(f"  Default language: '{settings.get('default_language', 'auto')}'")
        print(f"  Output folder: '{settings['output_folder_name']}'")
        print(f"  Max audio files: {settings['max_audio_files']}")
        print("\nLanguage options:")
        print("  --lang en    Force English (Pocket TTS)")
        print("  --lang nl    Force Dutch (Parkiet)")
        print("  --lang auto  Auto-detect language (default)")
        print("\nExamples:")
        print("  python Erika-tts.py --text \"Hello, I am Erika.\"")
        print("  python Erika-tts.py --text \"Hallo, ik ben Erika.\" --lang nl")
        print("  python Erika-tts.py --text \"Hello\" --voice azelma --output my_speech.wav")
        sys.exit(1)

    erika_tts_generate(text_to_generate, settings, voice, output_filename, language)

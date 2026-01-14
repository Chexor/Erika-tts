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

def load_settings(script_dir):
    settings_path = os.path.join(script_dir, SETTINGS_FILE)
    default_settings = {
        "default_voice": "azelma",
        "output_folder_name": "erika_tts_output",
        "max_audio_files": 5,
        "generation_settings": {
            "temperature": 0.7,
            "lsd_decode_steps": 1,
            "noise_clamp": None,
            "eos_threshold": -4.0,
            "frames_after_eos": None,
            "device": "cpu",
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
            # Update top-level settings
            for key, value in user_settings.items():
                if key != "generation_settings":
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
    venv_path = os.path.join(script_dir, "venv")
    python_exe = os.path.join(venv_path, "Scripts", "python.exe")

    if not os.path.isdir(venv_path):
        print(f"Error: Virtual environment not found at '{venv_path}'.")
        print("Please ensure 'venv' directory exists in the same location as this script.")
        sys.exit(1)
    if not os.path.exists(python_exe):
        print(f"Error: Python executable not found at '{python_exe}'.")
        print("Please ensure the virtual environment is correctly set up for Windows.")
        sys.exit(1)
    return python_exe

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


def erika_tts_generate(text_to_generate, settings, voice=None, custom_output_filename=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = ensure_output_folder_exists(script_dir, settings["output_folder_name"])

    # If voice is not provided by command line, use default from settings
    actual_voice = voice if voice is not None else settings["default_voice"]

    # Voice validation logic
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
        output_filename = f"erika_output_{timestamp}.wav"
    
    full_output_path = os.path.join(output_dir, output_filename)

    python_exe = get_venv_python(script_dir)

    # Construct the pocket-tts command using python -m pocket_tts
    command_args = [
        python_exe, "-m", "pocket_tts", "generate",
        "--text", text_to_generate,
        "--output-path", full_output_path
    ]
    if actual_voice:
        command_args.extend(["--voice", actual_voice])

    # Add generation settings from the config file
    gen_settings = settings["generation_settings"]
    for param, value in gen_settings.items():
        if value is not None:
            # Convert snake_case to kebab-case for CLI arguments
            command_args.extend([f"--{param.replace('_', '-')}", str(value)])

    print(f"\n--- Generating TTS ---")
    print(f"Text: \"{text_to_generate}\"")
    print(f"Voice: {actual_voice if actual_voice else 'Default (from settings)'}")
    print(f"Output: {full_output_path}")
    print(f"Executing: {' '.join(command_args)}")

    try:
        result = subprocess.run(command_args, check=True, capture_output=True, text=True)

        if result.stderr:
            print(result.stderr)

        if os.path.exists(full_output_path):
            print(f"\nTTS generated successfully at {full_output_path}")
            clean_old_audio_files(output_dir, settings["max_audio_files"])
            print("Playing audio...")
            wave_obj = sa.WaveObject.from_wave_file(full_output_path)
            play_obj = wave_obj.play()
            play_obj.wait_done()
        else:
            print(f"\nError: Expected output file '{full_output_path}' was not created.")
            if result.stderr:
                print(result.stderr)

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
        else:
            # If --text was not used, assume the first positional argument is the text
            if text_to_generate is None:
                text_to_generate = args[i]
            else:
                print(f"Warning: Unrecognized argument or duplicate text value '{args[i]}'. Ignoring.")
        i += 1

    if text_to_generate is None:
        print("Usage: python Erika-tts.py --text \"Your text here\" [--voice custom_voice_name_or_path] [--output custom_filename.wav]")
        print(f"Default voice (from settings): '{settings['default_voice']}'")
        print(f"Output folder (from settings): '{settings['output_folder_name']}'")
        print(f"Max audio files (from settings): {settings['max_audio_files']}")
        print("Example: python Erika-tts.py --text \"Hello, I am Erika.\"")
        print("Example: python Erika-tts.py \"Hello, I am Erika and I speak in a custom voice.\" --voice \"path/to/my_voice.wav\"")
        print("Example: python Erika-tts.py --text \"Custom named file.\" --output my_speech.wav")
        sys.exit(1)

    erika_tts_generate(text_to_generate, settings, voice, output_filename) # Pass settings to the function

"""
Handles the generation of audio from different TTS engines.
"""
import os
import subprocess
import torch
import soundfile as sf
from pocket_tts.models.tts_model import TTSModel
from pocket_tts.default_parameters import (
    DEFAULT_TEMPERATURE,
    DEFAULT_LSD_DECODE_STEPS,
    DEFAULT_NOISE_CLAMP,
    DEFAULT_EOS_THRESHOLD
)
from pocket_tts.modules.stateful_module import init_states
from pocket_tts.utils.utils import PREDEFINED_VOICES
import parkiet_engine

# --- English TTS Engine (PocketTTS) ---

_english_tts_model = None  # Global model instance for efficiency

def generate_english(text_to_generate, settings, voice, full_output_path):
    """Generate English speech using the Pocket TTS library directly."""
    global _english_tts_model

    print("Engine: Pocket TTS (English)")

    if _english_tts_model is None:
        print("Loading Pocket TTS model (this may take a moment on first run)...")
        gen_settings = settings.get("generation_settings", {})
        
        temp = gen_settings.get("temperature", DEFAULT_TEMPERATURE)
        lsd_decode_steps = gen_settings.get("lsd_decode_steps", DEFAULT_LSD_DECODE_STEPS)
        noise_clamp = gen_settings.get("noise_clamp", DEFAULT_NOISE_CLAMP)
        eos_threshold = gen_settings.get("eos_threshold", DEFAULT_EOS_THRESHOLD)
        device = gen_settings.get("device", "cpu")

        _english_tts_model = TTSModel.load_model(
            variant="b6369a24",  # Hardcoding variant as per README
            temp=temp,
            lsd_decode_steps=lsd_decode_steps,
            noise_clamp=noise_clamp,
            eos_threshold=eos_threshold,
        ).to(device)
        print(f"Pocket TTS model loaded on {device}")

    # Initialize model state
    model_state = init_states(_english_tts_model.flow_lm, batch_size=1, sequence_length=1000)

    # Handle voice conditioning
    if voice:
        if voice in PREDEFINED_VOICES:
            print(f"Using predefined voice: {voice}")
            model_state = _english_tts_model.get_state_for_audio_prompt(voice)
        elif os.path.exists(voice):
            print(f"Using custom voice from: {voice}")
            model_state = _english_tts_model.get_state_for_audio_prompt(voice)
        else:
            print(f"Warning: Voice '{voice}' not found as a predefined voice or file path. Using default voice.")
    else:
        print("Using default Pocket TTS voice.")

    print("Generating English speech...")
    audio_tensor = _english_tts_model.generate_audio(
        model_state=model_state,
        text_to_generate=text_to_generate,
        frames_after_eos=settings.get("generation_settings", {}).get("frames_after_eos"),
    )

    # Save the generated audio
    audio_data = audio_tensor.cpu().numpy()
    sf.write(full_output_path, audio_data, _english_tts_model.sample_rate)

    return os.path.exists(full_output_path)


# --- Dutch TTS Engine (Parkiet) ---

def generate_dutch(text_to_generate, settings, full_output_path):
    """Generate Dutch speech using Parkiet."""
    if not parkiet_engine.is_available():
        print("Error: Parkiet dependencies not installed.")
        print("Please run: pip install transformers soundfile torch")
        return False

    print("Engine: Parkiet (Dutch)")
    return parkiet_engine.generate_dutch_speech(
        text_to_generate,
        full_output_path,
        settings.get("parkiet_settings", {})
    )

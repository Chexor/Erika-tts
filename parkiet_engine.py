"""
Parkiet TTS Engine - Dutch text-to-speech using the Parkiet model.
"""
import os

# Lazy-loaded globals to avoid slow imports on startup
_model = None
_processor = None
_device = None


def _load_model(device="cuda"):
    """Lazy load the Parkiet model and processor."""
    global _model, _processor, _device
    import torch

    if _model is None or _device != device:
        print("Loading Parkiet model (this may take a moment on first run)...")
        from transformers import AutoProcessor, DiaForConditionalGeneration

        model_checkpoint = "pevers/parkiet"

        # Fall back to CPU if CUDA requested but not available
        if device == "cuda" and not torch.cuda.is_available():
            print("CUDA not available, falling back to CPU (this will be slower)")
            device = "cpu"

        _device = device

        _processor = AutoProcessor.from_pretrained(model_checkpoint)
        _model = DiaForConditionalGeneration.from_pretrained(model_checkpoint).to(_device)
        print(f"Parkiet model loaded on {_device}")

    return _model, _processor


def generate_dutch_speech(text, output_path, settings=None):
    """
    Generate Dutch speech using the Parkiet model.

    Args:
        text: The Dutch text to synthesize
        output_path: Path to save the output audio file
        settings: Dictionary with generation settings (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    import soundfile as sf

    # Default settings
    default_settings = {
        "device": "cuda",
        "max_new_tokens": 3072,
        "guidance_scale": 3.0,
        "temperature": 1.8,
        "top_p": 0.90,
        "top_k": 50,
    }

    if settings:
        default_settings.update(settings)

    device = default_settings.pop("device")

    try:
        model, processor = _load_model(device)

        # Use the actual device the model is on (may have fallen back to CPU)
        actual_device = _device

        # Parkiet expects speaker tags - add default [S1] if not present
        if "[S1]" not in text and "[S2]" not in text:
            text = f"[S1] {text}"

        # Process input - use actual_device which may have fallen back to CPU
        inputs = processor(text=text, padding=True, return_tensors="pt").to(actual_device)

        # Generate audio
        print("Generating Dutch speech...")
        outputs = model.generate(
            **inputs,
            **default_settings
        )

        # Decode and save
        audio_outputs = processor.batch_decode(outputs)

        # The processor returns audio arrays - save the first one
        if audio_outputs and len(audio_outputs) > 0:
            audio_data = audio_outputs[0]

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

            # Parkiet outputs at 44100 Hz sample rate
            sample_rate = 44100

            # Handle .wav extension (convert if needed)
            if output_path.endswith(".wav"):
                sf.write(output_path, audio_data, sample_rate)
            else:
                # Default to wav
                sf.write(output_path, audio_data, sample_rate)

            return True
        else:
            print("Error: No audio output generated")
            return False

    except Exception as e:
        print(f"Error generating Dutch speech: {e}")
        return False


def is_available():
    """Check if Parkiet dependencies are available."""
    try:
        import transformers
        import soundfile
        return True
    except ImportError:
        return False

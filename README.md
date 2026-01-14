# Erika TTS

A personalized Text-to-Speech wrapper using [Kyutai's Pocket TTS](https://github.com/kyutai-labs/pocket-tts) library with voice cloning capabilities.

## About Pocket TTS

Pocket TTS is a lightweight 100M parameter TTS model from [Kyutai](https://kyutai.org/tts) optimized for CPU execution.

**Key specs:**
- ~6x faster than real-time on modern CPUs
- ~200ms latency to first audio chunk
- Uses only 2 CPU cores
- Supports streaming audio generation
- English only (currently)
- Can process infinitely long text inputs

**Resources:**
- [GitHub](https://github.com/kyutai-labs/pocket-tts)
- [Hugging Face](https://huggingface.co/kyutai/pocket-tts)
- [Voices Repository](https://huggingface.co/kyutai/tts-voices)

## Setup

1. Create and activate virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Erika Wrapper Script (Recommended)

The `Erika-tts.py` script provides a convenient wrapper with automatic audio playback:

```bash
# Basic usage (if erika-tts.bat is in PATH)
erika-tts "Hello, this is a test."

# With custom voice
erika-tts "Hello" --voice alba

# With custom output filename
erika-tts "Hello" --output my_speech.wav
```

### Configuration

Edit `erika_settings.yaml` to customize defaults:

```yaml
default_voice: azelma
output_folder_name: erika_tts_output
max_audio_files: 5
generation_settings:
  temperature: 0.7
  lsd_decode_steps: 1
  device: cpu
```

### Available Voices

`alba`, `marius`, `javert`, `jean`, `fantine`, `cosette`, `eponine`, `azelma`

You can also use a path to a custom WAV file for voice cloning.

### Direct pocket-tts CLI

```bash
# Generate speech
pocket-tts generate --text "Hello world" --voice alba --output-path output.wav

# Start web API server
pocket-tts serve --host 0.0.0.0 --port 8000
```

## Generation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `temperature` | 0.7 | Controls randomness (higher = more varied) |
| `lsd_decode_steps` | 1 | Number of generation steps |
| `eos_threshold` | -4.0 | End-of-speech detection threshold |
| `device` | cpu | Use `cpu` or `cuda` |

## Python API

```python
from pocket_tts import TTSModel
import scipy.io.wavfile

# Load model (slow, do once)
tts_model = TTSModel.load_model()

# Load voice state (slow, cache if reusing)
voice_state = tts_model.get_state_for_audio_prompt("alba")
# Or use a custom WAV file:
# voice_state = tts_model.get_state_for_audio_prompt("path/to/voice.wav")
# Or from Hugging Face:
# voice_state = tts_model.get_state_for_audio_prompt("hf://kyutai/tts-voices/alba-mackenna/casual.wav")

# Generate audio (returns 1D torch tensor with PCM data)
audio = tts_model.generate_audio(voice_state, "Hello world, this is a test.")

# Save to file
scipy.io.wavfile.write("output.wav", tts_model.sample_rate, audio.numpy())
```

## Voice Cloning

You can clone any voice by providing a WAV file as the voice prompt. For best results:
- Use clean audio samples without background noise
- More voices available at [kyutai/tts-voices](https://huggingface.co/kyutai/tts-voices)

## Roadmap

Planned features:
- [ ] **File input** - Read text from a file (`--file input.txt`)
- [ ] **MP3 export** - Convert output to MP3 format
- [ ] **System tray app** - Background app with hotkey to speak selected text
- [ ] **Web API** - Local server for other apps to request TTS

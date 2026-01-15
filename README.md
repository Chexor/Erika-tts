# Erika TTS: High-Fidelity VibeVoice & Kokoro Integration

Erika TTS is a premium Text-to-Speech system designed for the Gemini CLI and general use, featuring state-of-the-art naturalness for both Dutch and English.

## Features
- **Microsoft VibeVoice (0.5B)**: Exclusive high-fidelity engine for "awesome" quality Dutch and English.
- **Cross-Lingual Support**: VibeVoice allows voices to speak multiple languages with natural accents.
- **Kokoro-ONNX**: Extremely fast and efficient English engine (maintained as a lightweight option).
- **Hybrid Architecture**: A Flask-based server handles model management and lazy loading to optimize VRAM usage.
- **Visible Worker**: Desktop notifications/popup windows for speech status.

## Setup

1. **Environment**:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Models**:
   - Ensure the `VibeVoice` repository is cloned in the root directory.
   - Download the `VibeVoice-Realtime-0.5B` model from Hugging Face if not present.
   - Place voice presets (.pt files) in `VibeVoice/demo/voices/streaming_model/`.

3. **Running the Server**:
   ```bash
   python tts_server.py
   ```
   The server runs on port `5050` and handles lazy initialization of models.

## Usage

### Gemini CLI (MCP)
Add Erika to your Gemini CLI as an MCP tool:
```bash
gemini mcp add voice python gemini_voice_mcp.py
```

### Direct Worker usage
```bash
python speak_worker.py --text "Hello world" --voice "en-Emma_woman"
```

## Configuration (`tts_config.json`)
Customize default engines and voices per language:
```json
{
    "en": {
        "engine": "vibevoice",
        "voice": "en-Emma_woman"
    },
    "nl": {
        "engine": "vibevoice",
        "voice": "nl-Spk1_woman"
    }
}
```

## Hardware Requirements
- **GPU**: NVIDIA RTX 30-series or higher recommended for VibeVoice (requires ~2GB VRAM).
- **OS**: Windows (optimized for PowerShell and `winsound`).

## Persona Defaults
- **Erika (English)**: Emma (`en-Emma_woman`)
- **Erika (Dutch)**: Spk1 (`nl-Spk1_woman`)

## Roadmap & Future Ideas
- [ ] **Windows Context Menu Integration**: Add a "Read with Erika" option to the Windows right-click menu for instant TTS of any selected text or file.
- [ ] **System-wide Hotkey**: Trigger speech for clipboard content using a global keyboard shortcut.
- [ ] **Voice Cloning Interface**: A simple UI to easily clone new voices by dropping a 5-10 second WAV file.
- [ ] **Streaming Playback**: Reduce latency further by playing audio chunks as they are generated.


import os
import sys
import logging
import tempfile
import traceback
import torch
import soundfile as sf
import copy
from flask import Flask, request, send_file, jsonify

# Monkey patch torch.load for VibeVoice compatibility
import torch
original_load = torch.load
def patched_load(*args, **kwargs):
    if 'weights_only' in kwargs:
        kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Configuration Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIBEVOICE_REPO_DIR = os.path.join(BASE_DIR, "VibeVoice")
VIBEVOICE_MODEL_PATH = "microsoft/VibeVoice-Realtime-0.5B"
VIBEVOICE_VOICES_DIR = os.path.join(VIBEVOICE_REPO_DIR, "demo", "voices", "streaming_model")

# Add VibeVoice to path
if VIBEVOICE_REPO_DIR not in sys.path:
    sys.path.append(VIBEVOICE_REPO_DIR)

from vibevoice.modular.modeling_vibevoice_streaming_inference import VibeVoiceStreamingForConditionalGenerationInference
from vibevoice.processor.vibevoice_streaming_processor import VibeVoiceStreamingProcessor

# --- Engine Initialization ---
vibe_model = None
vibe_processor = None
vibe_voices = {}

def get_vibevoice():
    global vibe_model, vibe_processor
    if vibe_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"Initializing VibeVoice on {device}...")
        try:
            vibe_processor = VibeVoiceStreamingProcessor.from_pretrained(VIBEVOICE_MODEL_PATH)
            vibe_model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(
                VIBEVOICE_MODEL_PATH,
                torch_dtype=(torch.bfloat16 if device == "cuda" else torch.float32),
                device_map=("cuda" if device == "cuda" else "cpu")
            )
            vibe_model.eval()
            vibe_model.set_ddpm_inference_steps(num_steps=2)
            logging.info("VibeVoice initialized with num_steps=2.")
        except Exception as e:
            logging.error(f"VibeVoice Init Failed: {e}")
            traceback.print_exc()
    return vibe_model, vibe_processor

def get_vibe_voice_preset(voice_name, lang, device):
    if voice_name not in vibe_voices:
        # Map simple names to PT files
        filename = f"{voice_name}.pt"
        path = os.path.join(VIBEVOICE_VOICES_DIR, filename)
        
        if not os.path.exists(path):
            # Try with language prefix if not provided
            if "_" not in voice_name and "-" not in voice_name:
                path = os.path.join(VIBEVOICE_VOICES_DIR, f"{lang}-{voice_name}.pt")
            
            if not os.path.exists(path):
                # Fallbacks
                if lang == "nl":
                    path = os.path.join(VIBEVOICE_VOICES_DIR, "nl-Spk1_woman.pt")
                else:
                    path = os.path.join(VIBEVOICE_VOICES_DIR, "en-Emma_woman.pt")
        
        logging.info(f"Loading VibeVoice preset: {path}")
        vibe_voices[voice_name] = torch.load(path, map_location=device, weights_only=False)
    return vibe_voices[voice_name]

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "running", 
        "engine": "vibevoice",
        "num_steps": 2,
        "supported_languages": ["en", "nl", "de", "fr", "it", "jp", "kr", "pl", "pt", "sp"]
    })

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    text = data.get('text')
    lang = data.get('lang', 'en')
    req_voice = data.get('voice')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    try:
        model, processor = get_vibevoice()
        if not model:
            return jsonify({"error": "VibeVoice not initialized"}), 500
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Determine default voice based on language if not provided
        if not req_voice:
            if lang == "nl":
                req_voice = "nl-Spk1_woman"
            else:
                req_voice = "en-Emma_woman"
                
        voice_segments = get_vibe_voice_preset(req_voice, lang, device)
        
        logging.info(f"Generating VibeVoice {lang} ({req_voice}) [2-steps]: {text[:30]}...")
        
        with torch.no_grad():
            inputs = processor.process_input_with_cached_prompt(
                text=text,
                cached_prompt=voice_segments,
                padding=True,
                return_tensors="pt",
                return_attention_mask=True
            )
            
            # Move tensors to device
            for k, v in inputs.items():
                if torch.is_tensor(v):
                    inputs[k] = v.to(device)
            
            outputs = model.generate(
                **inputs,
                cfg_scale=1.5,
                tokenizer=processor.tokenizer,
                generation_config={'do_sample': True, 'top_p': 0.8, 'temperature': 0.8},
                all_prefilled_outputs=copy.deepcopy(voice_segments),
                show_progress_bar=False,
                verbose=False
            )
        
        if outputs.speech_outputs and outputs.speech_outputs[0] is not None:
            # Cast to float32 for safety during conversion
            full_audio = torch.cat([s.to(torch.float32) for s in outputs.speech_outputs], dim=-1).cpu().numpy().flatten()
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name
            sf.write(output_path, full_audio, 24000)
            return send_file(output_path, mimetype="audio/wav")
        else:
            return jsonify({"error": "VibeVoice generated no audio"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {str(e)}"}), 500

if __name__ == '__main__':
    logging.info("Starting VibeVoice TTS Server on port 5050...")
    app.run(host='0.0.0.0', port=5050, threaded=True)

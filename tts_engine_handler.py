import sys
import os
import subprocess
import logging
import tempfile
import wave
import torch

# Monkey-patch torch.load to bypass weights_only=True default in torch 2.4+
# This is necessary because Coqui TTS uses older pickle files.
if not hasattr(torch, '_original_load'):
    torch._original_load = torch.load
    def _safe_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return torch._original_load(*args, **kwargs)
    torch.load = _safe_load

# Monkey-patch torchaudio.load to use soundfile directly
# This fixes the "TorchCodec required" error on nightly builds for Blackwell GPUs
try:
    import torchaudio
    import soundfile as sf
    
    def _safe_audio_load(path, **kwargs):
        # logging.info(f"Intercepted torchaudio.load for {path}")
        data, sr = sf.read(path)
        # sf.read returns (frames, channels) or (frames,)
        tensor = torch.from_numpy(data).float()
        if tensor.ndim == 1:
            tensor = tensor.unsqueeze(0)
        else:
            tensor = tensor.t()
        return tensor, sr
        
    torchaudio.load = _safe_audio_load
    logging.info("Patched torchaudio.load to use soundfile.")
except Exception as e:
    logging.warning(f"Failed to patch torchaudio: {e}")

# Try to import parkiet_engine (assume it's in the same dir)
try:
    import parkiet_engine
except ImportError:
    parkiet_engine = None

class TTSEngineHandler:
    _coqui_model = None  # Singleton for the heavy model

    def __init__(self, venv_python_path):
        self.venv_python = venv_python_path
        
    def _generate_coqui_tts(self, text, voice_path):
        """Generates speech using Coqui XTTS v2."""
        try:
            from TTS.api import TTS
            import torch
        except ImportError:
            logging.error("Coqui TTS not installed.")
            return None

        # Lazy load model
        if TTSEngineHandler._coqui_model is None:
            logging.info("Loading Coqui XTTS v2 model (this may take a while)...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logging.info(f"Using device: {device}")
            # Multilingual XTTS v2
            TTSEngineHandler._coqui_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        os.remove(output_path)  # Ensure clean path for generation
            
        logging.info(f"Generating Coqui XTTS audio... Voice: {voice_path}")
        try:
            # Check if voice file exists
            if not os.path.exists(voice_path):
                 logging.error(f"Voice sample not found: {voice_path}")
                 return None

            # Use direct generation and manual save for stability
            wav = TTSEngineHandler._coqui_model.tts(
                text=text,
                speaker_wav=voice_path,
                language="nl"
            )
            
            import soundfile as sf
            # XTTS v2 is 24000Hz
            sf.write(output_path, wav, 24000)
            
            if os.path.exists(output_path):
                return output_path
            else:
                logging.error("Coqui generation produced no file.")
                return None
        except Exception as e:
            logging.error(f"Coqui generation failed: {e}")
            return None
        except Exception as e:
            logging.error(f"Coqui generation failed: {e}")
            return None
        
    def _generate_parkiet_tts(self, text, voice="default"):
        """Generates Dutch speech using Parkiet engine."""
        if not parkiet_engine:
            logging.error("parkiet_engine module not found.")
            return None
            
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
            
        logging.info("Running Parkiet generation...")
        try:
            # Parkiet might take time to load model
            success = parkiet_engine.generate_dutch_speech(text, output_path)
            if success and os.path.exists(output_path):
                return output_path
            else:
                logging.error("Parkiet generation returned failure or no file.")
                return None
        except Exception as e:
            logging.error(f"Parkiet generation raised exception: {e}")
            return None

    def generate_speech(self, text, config, base_dir):
        """
        Generates speech using the configured engine.
        Returns path to audio file (generated or fallback).
        """
        engine = config.get("engine")
        voice = config.get("voice")
        output_path = None
        
        try:
            if engine == "pocket_tts":
                output_path = self._generate_pocket_tts(text, voice)
            elif engine == "system_tts":
                output_path = self._generate_system_tts(text, voice)
            elif engine == "parkiet":
                output_path = self._generate_parkiet_tts(text, voice)
            elif engine == "coqui-xtts":
                output_path = self._generate_coqui_tts(text, voice)
            else:
                logging.warning(f"Unknown engine: {engine}")
                return self._get_fallback(config, base_dir)

            if output_path and os.path.exists(output_path):
                return output_path
            else:
                logging.error("Generation produced no file.")
                return self._get_fallback(config, base_dir)

        except Exception as e:
            logging.error(f"Generation failed: {e}")
            return self._get_fallback(config, base_dir)

    def _get_fallback(self, config, base_dir):
        fallback_dir = os.path.join(base_dir, "fallback_audio")
        fallback_file = config.get("fallback_file")
        if fallback_file:
            path = os.path.join(fallback_dir, fallback_file)
            if os.path.exists(path):
                logging.info(f"Using fallback audio: {path}")
                return path
        logging.error("No fallback audio available.")
        return None

    def _generate_pocket_tts(self, text, voice):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        cmd = [
            self.venv_python, "-m", "pocket_tts", "generate",
            "--text", text,
            "--voice", voice,
            "--output-path", output_path,
            "--device", "cpu",
            "--temperature", "0.7",
            "--lsd-decode-steps", "1",
            "--eos-threshold", "-4.0"
        ]
        
        logging.info(f"Running generation command: {cmd}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            logging.error(f"pocket-tts failed: {result.stderr}")
            return None
            
        self._fix_wav_header(output_path)
        return output_path

    def _generate_system_tts(self, text, voice_name_fragment):
        """Generates audio using Windows SAPI (System.Speech) via PowerShell."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name

        # PowerShell script to output SAPI speech to file
        # We try to match the voice name partially
        ps_script = f"""
        Add-Type -AssemblyName System.Speech;
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;
        
        # Try to select voice
        $voices = $synth.GetInstalledVoices();
        $selected = $null;
        foreach ($v in $voices) {{
            if ($v.VoiceInfo.Name -like "*{voice_name_fragment}*") {{
                $selected = $v;
                break;
            }}
        }}
        
        if ($selected) {{
            $synth.SelectVoice($selected.VoiceInfo.Name);
        }}
        
        $synth.SetOutputToWaveFile("{output_path}");
        $synth.Speak("{text}");
        $synth.Dispose();
        """
        
        logging.info(f"Running System TTS generation (Voice filter: {voice_name_fragment})...")
        try:
            subprocess.run(
                ["powershell", "-c", ps_script],
                check=True,
                timeout=30
            )
            return output_path
        except Exception as e:
            logging.error(f"System TTS failed: {e}")
            return None

    def _fix_wav_header(self, path):
        try:
            with wave.open(path, 'rb') as wf:
                params = wf.getparams()
                frames = wf.getnframes()
                
                if frames >= 1000000000: # Corrupt frame count check
                    logging.info(f"Fixing corrupt WAV header (frames={frames})")
                    data = wf.readframes(frames)
                    real_frames = len(data) // (params.nchannels * params.sampwidth)
                    wf.close()
                    
                    with wave.open(path, 'wb') as fixed_wf:
                        fixed_wf.setparams(params)
                        fixed_wf.setnframes(real_frames)
                        fixed_wf.writeframes(data)
                    logging.info("WAV header fixed.")
        except Exception as e:
            logging.error(f"Error fixing WAV header: {e}")

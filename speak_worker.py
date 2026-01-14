import argparse
import sys
import os
import subprocess
import tempfile
import logging
import time

# Configuration
ALLOWED_VOICES = ['alba', 'marius', 'javert', 'jean', 'fantine', 'cosette', 'eponine', 'azelma']
DEFAULT_VOICE = "azelma"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, "venv", "Scripts", "python.exe")

# Setup logging
logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, "worker_debug.log"),
    level=logging.INFO,
    format='%(asctime)s - WORKER - %(levelname)s - %(message)s',
    force=True
)

def get_voice_path(voice: str) -> str:
    """Resolve voice name or path."""
    if voice in ALLOWED_VOICES:
        return voice
    if os.path.exists(voice):
        return voice
    return DEFAULT_VOICE

def perform_speech(text, voice):
    logging.info(f"Worker started for text: {text[:50]}...")
    
    output_path = None
    try:
        actual_voice = get_voice_path(voice)
        logging.info(f"Resolved voice: {actual_voice}")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        logging.info(f"Created temp file: {output_path}")

        # Build pocket-tts command with default settings mirroring Erika-tts.py
        cmd = [
            VENV_PYTHON, "-m", "pocket_tts", "generate",
            "--text", text,
            "--voice", actual_voice,
            "--output-path", output_path,
            "--device", "cpu",
            "--temperature", "0.7",
            "--lsd-decode-steps", "1",
            "--eos-threshold", "-4.0"
        ]
        
        logging.info(f"Running generation command...")
        
        # Synchronous subprocess run is fine here since this whole script is the background worker
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            logging.error(f"Generation failed: {result.stderr}")
            return

        logging.info("Generation successful")
        
        if not os.path.exists(output_path):
            logging.error("Audio file missing")
            return

        # Validate and Fix WAV file
        try:
            import wave
            with wave.open(output_path, 'rb') as wf:
                params = wf.getparams()
                frames = wf.getnframes()
                
                # Check for bogus frame count (pocket-tts streaming issue)
                if frames >= 1000000000:
                    logging.info(f"Detected corrupt WAV header (frames={frames}). Fixing...")
                    # Read all data until EOF
                    data = wf.readframes(frames)
                    real_frames = len(data) // (params.nchannels * params.sampwidth)
                    logging.info(f"Real valid frames: {real_frames}")
                    
                    # We need to close read handle before writing
                    wf.close()
                    
                    # Rewrite the file with correct header
                    with wave.open(output_path, 'wb') as fixed_wf:
                        fixed_wf.setparams(params)
                        fixed_wf.setnframes(real_frames)
                        fixed_wf.writeframes(data)
                    
                    logging.info("WAV header fixed.")
                else:
                    logging.info(f"WAV params valid: frames={frames}")
                    
        except Exception as e:
            logging.error(f"Error checking/fixing WAV: {e}")
            # If fix failed, we might want to return, but let's try playing anyway
            
        
        # Playback using Powershell (headless and robust with fixed WAV)
        try:
            logging.info("Attempting playback with Powershell")
            # We use a specific Powershell command that loads the sound player, plays it, and waits.
            ps_cmd = f'(New-Object Media.SoundPlayer "{output_path}").PlaySync()'
            
            # Measure time
            start_time = time.time()
            subprocess.run(["powershell", "-c", ps_cmd], check=True)
            elapsed = time.time() - start_time
            
            logging.info(f"Playback finished in {elapsed:.2f}s")
            
        except Exception as e:
            logging.error(f"Playback error: {e}")
            # Fallback to os.startfile if Powershell fails
            try:
                logging.info("Fallback to os.startfile")
                os.startfile(output_path)
                time.sleep(5)
            except:
                pass

    except Exception as e:
        logging.critical(f"Worker crashed: {e}")
    finally:
        if output_path and os.path.exists(output_path):
            try:
                os.unlink(output_path)
                logging.info("Cleaned up temp file")
            except:
                pass
        logging.info("Worker finished")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--text", required=True)
        parser.add_argument("--voice", default=DEFAULT_VOICE)
        args = parser.parse_args()
        
        perform_speech(args.text, args.voice)
    except Exception as e:
        import traceback
        sys.stderr.write(f"Worker crashed: {e}\n")
        traceback.print_exc()
        sys.exit(1)

"""
MCP Server for Erika TTS (VibeVoice)

Provides tools to speak text in multiple languages using high-quality VibeVoice models.
Add to Gemini with: gemini mcp add voice python gemini_voice_mcp.py
"""

import os
import sys
import json
import logging
import subprocess
import requests
from mcp.server import FastMCP

# Initialize MCP server
mcp = FastMCP("erika-voice")

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")
ALLOWED_VOICES = {
    'en-Emma_woman': 'Native English - Professional & Clear',
    'en-Grace_woman': 'Native English - Warm & Natural',
    'en-Wayne_man': 'Native English - Deep & Authoritative',
    'nl-Spk1_woman': 'Native Dutch - High Quality Female',
    'de-Spk1_woman': 'German Female (Cross-lingual capable)',
    'fr-Spk1_woman': 'French Female (Cross-lingual capable)'
}
DEFAULT_VOICE_EN = "en-Emma_woman"
DEFAULT_VOICE_NL = "nl-Spk1_woman"

# Set up logging to file
logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, "mcp_debug.log"),
    level=logging.INFO,
    format='%(asctime)s - MCP - %(levelname)s - %(message)s',
    force=True
)

def spawn_worker(text: str, voice: str):
    """Refactored worker spawning logic."""
    worker_script = os.path.join(SCRIPT_DIR, "speak_worker.py")
    cmd = [VENV_PYTHON, worker_script, "--text", text, "--voice", voice]
    
    logging.info(f"Spawning worker: {cmd}")
    try:
        # 0x00000010 = CREATE_NEW_CONSOLE | 0x00000200 = NEW_PROCESS_GROUP
        subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=0x00000010 | 0x00000200
        )
        return True
    except Exception as e:
        logging.error(f"Failed to spawn worker: {e}")
        return False

@mcp.tool()
async def speak(text: str, lang: str = "en", voice: str = None) -> str:
    """
    Speak text using a specific language and voice.
    Use this for precise control over the output.

    Args:
        text (str): The text to speak.
        lang (str): Language code ('en' or 'nl').
        voice (str): Optional voice name from list_voices().
    """
    if not text or not text.strip():
        return "Error: No text provided"

    # Resolve default voice based on language if not provided
    if not voice:
        voice = DEFAULT_VOICE_NL if lang == "nl" else DEFAULT_VOICE_EN
    
    if voice not in ALLOWED_VOICES:
        logging.warning(f"Voice {voice} not in allowed list, but attempting anyway...")

    if spawn_worker(text, voice):
        return f"🔊 Speaking ({lang}) using {voice}..."
    return "Error: Could not start speech worker"

@mcp.tool()
async def speak_english(text: str) -> str:
    """
    Speak text in English using the default Erika (Emma) voice.
    Use this for standard English responses.
    """
    return await speak(text, lang="en", voice=DEFAULT_VOICE_EN)

@mcp.tool()
async def speak_dutch(text: str) -> str:
    """
    Speak text in Dutch using the high-quality Dutch Erika voice.
    Use this for all Dutch responses.
    """
    return await speak(text, lang="nl", voice=DEFAULT_VOICE_NL)

@mcp.tool()
def list_voices() -> str:
    """
    List available VibeVoice models and their descriptions.
    """
    lines = ["Available VibeVoice Persona Models:"]
    for v, desc in ALLOWED_VOICES.items():
        lines.append(f"- {v}: {desc}")
    return "\n".join(lines)

@mcp.tool()
def check_server_status() -> str:
    """
    Verify the VibeVoice TTS Backend server status.
    """
    try:
        response = requests.get("http://localhost:5050/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return f"✅ Backend Online: {data.get('engine')} engine is ready."
        return f"⚠️ Backend warning: Received status {response.status_code}"
    except Exception as e:
        return f"❌ Backend Offline: Ensure 'python tts_server.py' is running. ({str(e)})"

if __name__ == "__main__":
    logging.info("Starting Erika MCP Voice Server...")
    mcp.run()


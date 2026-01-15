"""
MCP Server for Gemini CLI Voice Mode

Provides a 'speak' tool that converts text to speech using pocket-tts.
Add to Gemini with: gemini mcp add voice python gemini_voice_mcp.py
"""

import os
import sys
import tempfile
import subprocess
import logging
from mcp.server import FastMCP

# Initialize MCP server
mcp = FastMCP("gemini-voice")

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "Scripts", "python.exe")
ALLOWED_VOICES = ['en-Emma_woman', 'en-Grace_woman', 'en-Wayne_man', 'nl-Spk1_woman']
DEFAULT_VOICE = "en-Emma_woman"


def get_voice_path(voice: str) -> str:
    """Resolve voice name."""
    if voice in ALLOWED_VOICES:
        return voice
    return DEFAULT_VOICE


import asyncio

# Set up logging to file
# Use force=True to override any existing logging config from FastMCP/libraries
logging.basicConfig(
    filename=os.path.join(SCRIPT_DIR, "mcp_debug.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

def spawn_worker(text: str, voice: str):
    """Refactored worker spawning logic."""
    worker_script = os.path.join(SCRIPT_DIR, "speak_worker.py")
    
    # Use standard python.exe to allow console window (User request: visible window)
    cmd = [VENV_PYTHON, worker_script, "--text", text, "--voice", voice]
    
    logging.info(f"Spawning worker: {cmd}")
    
    try:
        # User wants a visible window, top-left.
        # We need CREATE_NEW_CONSOLE (0x00000010) to force a separate window.
        # We keep DETACHED_PROCESS/NEW_GROUP to avoid blocking.
        
        subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=0x00000010 | 0x00000200 # CREATE_NEW_CONSOLE | NEW_GROUP
        )
        logging.info("Worker spawned successfully (visible console)")
        return True
    except Exception as e:
        logging.error(f"Failed to spawn worker: {e}")
        return False

@mcp.tool()
async def speak_english(text: str) -> str:
    """
    Speak text in English using high-quality Microsoft VibeVoice.
    Use this for all English responses.

    Args:
        text: The English text to speak.
    """
    if not text or not text.strip():
        return "Error: No text provided"

    logging.info(f"Received English speak request: {text[:50]}...")
    if spawn_worker(text, "en-Emma_woman"):
        return "🔊 Speaking (English)..."
    return "Error starting speech"

@mcp.tool()
async def speak_dutch(text: str) -> str:
    """
    Speak text in Dutch using the "awesome" quality Microsoft VibeVoice engine.
    Use this for all Dutch responses.

    Args:
        text: The Dutch text to speak.
    """
    if not text or not text.strip():
        return "Error: No text provided"

    logging.info(f"Received Dutch speak request: {text[:50]}...")
    if spawn_worker(text, "nl-Spk1_woman"):
        return "🔊 Spreken (Nederlands)..."
    return "Error starting speech"

@mcp.tool()
def list_voices() -> str:
    """
    List available VibeVoice models.

    Returns:
        List of available voice names
    """
    return f"Available VibeVoice models: {', '.join(ALLOWED_VOICES)}\nDefault: {DEFAULT_VOICE}"


if __name__ == "__main__":
    # Spoken notification on startup
    spawn_worker("Voice server ready", DEFAULT_VOICE)
    mcp.run()

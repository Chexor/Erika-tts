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
ALLOWED_VOICES = ['alba', 'marius', 'javert', 'jean', 'fantine', 'cosette', 'eponine', 'azelma']
DEFAULT_VOICE = "azelma"


def get_voice_path(voice: str) -> str:
    """Resolve voice name or path."""
    if voice in ALLOWED_VOICES:
        return voice
    if os.path.exists(voice):
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
async def speak(text: str, voice: str = DEFAULT_VOICE) -> str:
    """
    Convert text to speech and play it aloud.

    Use this tool to speak your responses to the user. Call this at the end of
    your response when you want the user to hear what you're saying.

    Args:
        text: The text to convert to speech and play aloud
        voice: Voice to use (alba, marius, javert, jean, fantine, cosette, eponine, azelma) or path to WAV file

    Returns:
        Confirmation that the speech generation has started
    """
    if not text or not text.strip():
        return "Error: No text provided to speak"

    logging.info(f"Received speak request for: {text[:50]}...")
    
    if spawn_worker(text, voice):
        return "🔊 Speaking..."
    else:
        return "Error starting speech"


@mcp.tool()
def list_voices() -> str:
    """
    List available voices for text-to-speech.

    Returns:
        List of available voice names
    """
    return f"Available voices: {', '.join(ALLOWED_VOICES)}\nDefault voice: {DEFAULT_VOICE}"


if __name__ == "__main__":
    # Spoken notification on startup
    spawn_worker("Voice server ready", DEFAULT_VOICE)
    mcp.run()

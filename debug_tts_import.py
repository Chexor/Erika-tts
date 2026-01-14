import sys
import traceback

print("Attempting to import TTS...")
try:
    from TTS.api import TTS
    print("Success!")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Exception: {e}")
    traceback.print_exc()

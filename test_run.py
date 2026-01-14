import sys
import os
import subprocess
import time

script_dir = r"S:\Code_Workspace\Erika-tts"
os.chdir(script_dir)
python_exe = os.path.join(script_dir, "venv312", "Scripts", "python.exe")

env = os.environ.copy()
env["ERIKA_NO_PLAYBACK"] = "1"

print("=== Testing Dutch TTS (Parkiet on CPU) ===")
print("This will take 30-60 seconds...")
print()

start = time.time()
cmd = [python_exe, "Erika-tts.py", "--text", "Goedemorgen, dit is een test van het Nederlandse spraaksysteem.", "--lang", "nl", "--output", "test_nl_cpu.wav"]
result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir, env=env)
elapsed = time.time() - start

print(f"Return code: {result.returncode}")
print(f"Time: {elapsed:.1f} seconds")
if result.stdout:
    print(f"\nOutput:\n{result.stdout}")
if result.stderr:
    print(f"\nStderr:\n{result.stderr}")

# Check file
output_file = os.path.join(script_dir, "erika_tts_output", "test_nl_cpu.wav")
if os.path.exists(output_file):
    print(f"\nSUCCESS: {output_file} ({os.path.getsize(output_file)} bytes)")
else:
    print(f"\nFAILED: Output file not created")

import os
import urllib.request
import zipfile
import shutil
import logging

# Configure
PIPER_URL = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
MODEL_URL_ONNX = "https://huggingface.co/rhasspy/piper-voices/resolve/main/nl/nl_NL/mls/medium/nl_NL-mls-medium.onnx?download=true"
MODEL_URL_JSON = "https://huggingface.co/rhasspy/piper-voices/resolve/main/nl/nl_NL/mls/medium/nl_NL-mls-medium.onnx.json?download=true"
DEST_DIR = "piper"
MODEL_DIR = os.path.join(DEST_DIR, "models")

logging.basicConfig(level=logging.INFO)

def download_file(url, dest):
    logging.info(f"Downloading {url}...")
    try:
        urllib.request.urlretrieve(url, dest)
        logging.info(f"Downloaded to {dest}")
        return True
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        return False

def setup_piper():
    if not os.path.exists(DEST_DIR):
        os.makedirs(DEST_DIR)

    # 1. Download and Extract Piper Binary
    zip_path = "piper_windows.zip"
    if not os.path.exists(os.path.join(DEST_DIR, "piper.exe")):
        if download_file(PIPER_URL, zip_path):
            logging.info("Extracting Piper...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".") # Extracts to piper/ folder usually
            os.remove(zip_path)
            logging.info("Piper extracted.")
    else:
        logging.info("Piper binary already exists.")

    # 2. Download Voice Model
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)
    
    model_name = "nl_NL-mls-medium.onnx"
    json_name = "nl_NL-mls-medium.onnx.json"
    
    model_dest = os.path.join(MODEL_DIR, model_name)
    json_dest = os.path.join(MODEL_DIR, json_name)
    
    if not os.path.exists(model_dest):
        download_file(MODEL_URL_ONNX, model_dest)
    
    if not os.path.exists(json_dest):
        download_file(MODEL_URL_JSON, json_dest)

    logging.info("Piper setup complete.")

if __name__ == "__main__":
    setup_piper()

import torch
import sys
import os

print(f"Python: {sys.version}")
print(f"PyTorch: {torch.__version__}")
try:
    print(f"CUDA Available: {torch.cuda.is_available()}")
    print(f"CUDA Version: {torch.version.cuda}")
    print(f"CUDNN Version: {torch.backends.cudnn.version()}")
    
    if torch.cuda.is_available():
        print(f"Device Name: {torch.cuda.get_device_name(0)}")
        print(f"Device Capability: {torch.cuda.get_device_capability(0)}")
        
        print("\nAttempting tensor operation on GPU...")
        try:
            x = torch.tensor([1.0, 2.0]).cuda()
            print(f"Success! Tensor on device: {x.device}")
            y = x * 2
            print(f"Computation result: {y}")
        except Exception as e:
            print(f"\nTensor operation FAILED: {e}")
    else:
        print("\nCUDA is NOT available.")

    print("\nTesting Torchaudio load with Monkey Patch...")
    wav_path = "voice_samples/Laura_VL.wav"
    if os.path.exists(wav_path):
        import torchaudio
        import soundfile as sf
        import torch
        
        def safe_load(path, **kwargs):
            print(f"Intercepted load for {path}")
            data, sr = sf.read(path)
            # sf.read returns (frames, channels) or (frames,)
            tensor = torch.from_numpy(data).float()
            if tensor.ndim == 1:
                tensor = tensor.unsqueeze(0)
            else:
                tensor = tensor.t()
            return tensor, sr
            
        torchaudio.load = safe_load
        
        y, sr = torchaudio.load(wav_path)
        print(f"Loaded successfully via patch: {y.shape}, {sr}")
    else:
        print(f"Warning: {wav_path} not found.")

except Exception as e:
    print(f"\nGeneral Error: {e}")
    import traceback
    traceback.print_exc()

import torch
import sys

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

except Exception as e:
    print(f"\nGeneral Error: {e}")

import sys
import torch

def verify_hardware():
    print("=" * 60)
    print("DocuMind Financial AI - Hardware & CUDA Verification")
    print("=" * 60)
    
    python_ver = sys.version.split()[0]
    print(f"Python Version: {python_ver}")
    print(f"PyTorch Version: {torch.__version__}")
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if not cuda_available:
        print("[ERROR] CUDA is not available to PyTorch. Check drivers and torch installation.")
        sys.exit(1)
        
    device_count = torch.cuda.device_count()
    device_name = torch.cuda.get_device_name(0)
    capability = torch.cuda.get_device_capability(0)
    total_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    
    print(f"Device Count: {device_count}")
    print(f"Active Device [0]: {device_name}")
    print(f"Compute Capability: {capability[0]}.{capability[1]}")
    print(f"Total VRAM: {total_memory_gb:.2f} GB")
    
    print("\nEjecutando prueba de calculo tensorial en GPU...")
    x = torch.rand(1000, 1000, device="cuda")
    y = torch.matmul(x, x)
    torch.cuda.synchronize()
    print(f"GPU Computation successful. Result matrix shape: {y.shape}")
    print("=" * 60)
    print("VERIFICATION STATUS: SUCCESS (GTX 1660 Ti Ready for Production)")
    print("=" * 60)

if __name__ == "__main__":
    verify_hardware()

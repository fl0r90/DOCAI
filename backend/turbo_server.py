import os
import subprocess
import sys

# Wrapper pentru TurboQuant+ (TheTom/turboquant_plus)
# Setează KV Cache la K=8 (q8_0) și V=4 (turbo4) conform directivei boss-ului.

MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/import/google_gemma-4-E4B-it-Q4_K_M.gguf")
CTX_SIZE = os.getenv("CHAT_CTX", "32768")
GPU_LAYERS = os.getenv("GPU_LAYERS", "99")
PORT = os.getenv("PORT", "8000")

def launch():
    print(f"[*] TURBO-SERVER: Pornire cu K=q8_0, V=turbo4 (PolarQuant 4-bit)")
    
    cmd = [
        "/app/bin/llama-server",
        "-m", MODEL_PATH,
        "-c", CTX_SIZE,
        "-ngl", GPU_LAYERS,
        "--port", PORT,
        "--host", "0.0.0.0",
        "-ctk", "q8_0",    # Key Cache: 8-bit precision
        "-ctv", "turbo4",  # Value Cache: 4-bit compression (PolarQuant)
        "--flash-attn", "on"
    ]

    # Inlocuim procesul wrapper cu llama-server
    os.execv(cmd[0], cmd)

if __name__ == "__main__":
    launch()

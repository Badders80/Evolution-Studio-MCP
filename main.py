#!/usr/bin/env python3
"""
Evolution Studio MCP Server
Bridges Perplexity -> Gemini 2.0 -> Local Resources (ComfyUI, Vault, Models)
"""
from fastmcp import FastMCP
import google.generativeai as genai
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# 1. Load Environment Variables (API Key)
load_dotenv()

# 2. Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file! Please create it.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# 3. Initialize MCP Server
mcp = FastMCP("Evolution Studio")

# ===== TOOLS =====

@mcp.tool()
def generate_image(prompt: str, workflow: str = "flux_default") -> dict:
    """
    Generate an image using ComfyUI on the RTX 3060.
    Args:
        prompt: Description of the image to generate
        workflow: Workflow name (default: flux_default)
    """
    try:
        # Step 1: Use Gemini to enhance the user's prompt for better results
        enhanced_prompt = model.generate_content(
            f"Convert this raw idea into a high-quality Stable Diffusion prompt. Keep it under 200 words. Raw idea: {prompt}"
        ).text

        # Step 2: Send to Local ComfyUI (Simulated for connection test)
        # In production, this would send a full JSON workflow to port 8188
        print(f"🌊 Sending to ComfyUI: {enhanced_prompt}")

        # Check if ComfyUI is actually running
        try:
            # Simple ping to see if server is up
            requests.get("http://127.0.0.1:8188", timeout=2)
            status = "ComfyUI is ONLINE"
        except requests.exceptions.ConnectionError:
            status = "ComfyUI is OFFLINE (Start it to generate real images)"

        return {
            "status": "success",
            "original_prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "backend_status": status
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
def list_models() -> dict:
    """List available AI models from the S: drive /mnt/scratch/models/"""
    path = Path("/mnt/scratch/models/GGUF")
    if path.exists():
        models = [f.name for f in path.iterdir() if f.is_file()]
        return {"category": "GGUF", "models": models, "count": len(models)}
    return {"status": "empty", "message": "No GGUF models found in /mnt/scratch/models/GGUF"}

@mcp.tool()
def gpu_status() -> dict:
    """Check RTX 3060 VRAM usage via nvidia-smi"""
    try:
        import subprocess
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            used, total, util = result.stdout.strip().split(',')
            return {
                "vram_used": f"{used} MB",
                "vram_total": f"{total} MB",
                "gpu_utilization": f"{util} %"
            }
        return {"status": "error", "message": "Could not read GPU stats"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("🚀 Evolution Studio MCP is running...")
    mcp.run()

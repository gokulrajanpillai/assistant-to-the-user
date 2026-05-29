"""
ATHU (Assistant to the User) - Setup Script
First-run installer for dependencies, models, and configuration.
"""

import subprocess
import sys
import os
import json
import shutil
from pathlib import Path


def run(cmd, check=True):
    print(f"  Running: {cmd}")
    result = subprocess.run(cmd, shell=True, check=check, capture_output=False)
    return result.returncode == 0


def install_python_deps():
    print("\n[1/5] Installing Python dependencies...")
    run(f"{sys.executable} -m pip install --upgrade pip")
    run(f"{sys.executable} -m pip install -r requirements.txt")


def install_ollama():
    print("\n[2/5] Checking Ollama...")
    if shutil.which("ollama"):
        print("  Ollama already installed.")
    else:
        print("  Ollama not found. Please install from: https://ollama.ai")
        print("  After installing, run: ollama pull llama3.2:3b")


def setup_piper_tts():
    print("\n[3/5] Setting up Piper TTS...")
    voice_dir = Path("data/models/tts")
    voice_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Place Piper voice files in: {voice_dir}")
    print("  Download voices from: https://huggingface.co/rhasspy/piper-voices")


def create_default_config():
    print("\n[4/5] Creating default config...")
    config_path = Path("config.json")
    if config_path.exists():
        print("  config.json already exists, skipping.")
        return
    default_config = {
        "user": {"name": "Sir", "timezone": "America/New_York", "interests": [], "goals": []},
        "llm": {"routing": "prefer_free", "free_model": "llama3.2:3b", "ollama_base_url": "http://localhost:11434"},
        "voice": {"wake_word": "hey_jarvis", "tts_voice": "en_GB-alan-medium", "stt_model": "base.en"},
        "modules": {
            "filesystem": {"enabled": True, "write_access": False, "root_paths": []},
            "websearch": {"enabled": True, "brave_api_key": ""},
            "trading": {"enabled": False, "dry_run": True, "broker": "alpaca"},
            "youtube": {"enabled": False},
            "fitness": {"enabled": True, "checkin_times": ["07:00", "20:00"]},
            "advisor": {"enabled": True, "briefing_time": "07:05", "debrief_time": "21:00"}
        },
        "api_keys": {"openai": "", "anthropic": "", "alpaca_key": "", "alpaca_secret": ""},
        "server": {"host": "127.0.0.1", "port": 8080, "ws_secret": ""}
    }
    with open(config_path, "w") as f:
        json.dump(default_config, f, indent=2)
    print("  config.json created.")


def create_directories():
    for d in ["data/chroma", "data/models/tts", "data/models/wakeword", "logs"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    print("  Directory structure created.")


if __name__ == "__main__":
    print("=" * 60)
    print("  ATHU - Assistant to the User  |  Setup")
    print("=" * 60)
    create_directories()
    install_python_deps()
    install_ollama()
    setup_piper_tts()
    create_default_config()
    print("\n  Setup complete! Edit config.json, then run: python main.py")
    print("=" * 60)

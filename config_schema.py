"""
Pydantic schema for config.json validation.
"""
from pydantic import BaseModel
from typing import Optional, List


class UserConfig(BaseModel):
    name: str = "Sir"
    timezone: str = "America/New_York"
    interests: List[str] = []
    goals: List[str] = []


class LLMConfig(BaseModel):
    routing: str = "prefer_free"
    free_model: str = "llama3.2:3b"
    premium_model_trading: str = "gpt-4o"
    ollama_base_url: str = "http://localhost:11434"


class VoiceConfig(BaseModel):
    wake_word: str = "hey_jarvis"
    tts_voice: str = "en_GB-alan-medium"
    stt_model: str = "base.en"
    input_device: Optional[int] = None
    output_device: Optional[int] = None


class FilesystemModuleConfig(BaseModel):
    enabled: bool = True
    write_access: bool = False
    root_paths: List[str] = []


class TradingModuleConfig(BaseModel):
    enabled: bool = False
    dry_run: bool = True
    broker: str = "alpaca"


class ModulesConfig(BaseModel):
    filesystem: FilesystemModuleConfig = FilesystemModuleConfig()
    websearch: dict = {"enabled": True, "brave_api_key": ""}
    trading: TradingModuleConfig = TradingModuleConfig()
    youtube: dict = {"enabled": False}
    fitness: dict = {"enabled": True, "checkin_times": ["07:00", "20:00"]}
    advisor: dict = {"enabled": True, "briefing_time": "07:05", "debrief_time": "21:00"}


class APIKeysConfig(BaseModel):
    openai: str = ""
    anthropic: str = ""
    alpaca_key: str = ""
    alpaca_secret: str = ""
    youtube_client_id: str = ""
    brave_search: str = ""


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8080
    ws_secret: str = ""


class ATHUConfig(BaseModel):
    user: UserConfig = UserConfig()
    llm: LLMConfig = LLMConfig()
    voice: VoiceConfig = VoiceConfig()
    modules: ModulesConfig = ModulesConfig()
    api_keys: APIKeysConfig = APIKeysConfig()
    server: ServerConfig = ServerConfig()

"""
ATHU Voice - Text to Speech
Uses Piper TTS (local, free, realistic neural voices).
Falls back to pyttsx3 (system TTS) if Piper is unavailable.
"""

import threading
import logging
import io

logger = logging.getLogger("athu.tts")


class TextToSpeech:
    """
    Wraps Piper TTS for high-quality local speech synthesis.
    Voice: en_GB-alan-medium (British English, matches ATHU persona).
    All speech is non-blocking via a background thread.
    """

    def __init__(self, voice: str = "en_GB-alan-medium"):
        self.voice = voice
        self._piper = None
        self._fallback = None
        self._speak_lock = threading.Lock()
        self._load()

    def _load(self):
        try:
            from piper.voice import PiperVoice
            import wave
            voice_path = f"data/models/tts/{self.voice}.onnx"
            import os
            if os.path.exists(voice_path):
                self._piper = PiperVoice.load(voice_path)
                logger.info(f"Piper TTS loaded: {self.voice}")
            else:
                logger.warning(
                    f"Piper voice file not found: {voice_path}. "
                    "Download from https://huggingface.co/rhasspy/piper-voices"
                )
                self._load_fallback()
        except ImportError:
            logger.warning("Piper TTS not installed. Using pyttsx3 fallback.")
            self._load_fallback()
        except Exception as e:
            logger.error(f"Piper TTS load error: {e}")
            self._load_fallback()

    def _load_fallback(self):
        try:
            import pyttsx3
            self._fallback = pyttsx3.init()
            self._fallback.setProperty("rate", 185)
            # Try to find a British English voice
            voices = self._fallback.getProperty("voices")
            for v in voices:
                if "en_gb" in v.id.lower() or "english" in v.name.lower():
                    self._fallback.setProperty("voice", v.id)
                    break
            logger.info("pyttsx3 fallback TTS loaded.")
        except Exception as e:
            logger.error(f"TTS fallback also failed: {e}. No speech output available.")

    def speak(self, text: str):
        """Speak text synchronously (blocks until done)."""
        if not text.strip():
            return
        with self._speak_lock:
            if self._piper:
                self._speak_piper(text)
            elif self._fallback:
                self._speak_pyttsx3(text)
            else:
                logger.warning(f"No TTS available. Would say: {text!r}")

    def speak_async(self, text: str):
        """Speak text in a background thread (non-blocking)."""
        if not text.strip():
            return
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()

    def _speak_piper(self, text: str):
        try:
            import sounddevice as sd
            import numpy as np
            audio_bytes = io.BytesIO()
            import wave
            with wave.open(audio_bytes, "wb") as wav_file:
                self._piper.synthesize(text, wav_file)
            audio_bytes.seek(0)
            with wave.open(audio_bytes, "rb") as wav_file:
                sr = wav_file.getframerate()
                frames = wav_file.readframes(wav_file.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
            sd.play(audio, samplerate=sr, blocking=True)
        except Exception as e:
            logger.error(f"Piper speak error: {e}")

    def _speak_pyttsx3(self, text: str):
        try:
            self._fallback.say(text)
            self._fallback.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 speak error: {e}")

    @property
    def is_available(self) -> bool:
        return self._piper is not None or self._fallback is not None

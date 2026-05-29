"""
ATHU Voice - Speech to Text
Uses faster-whisper (local, free, CPU-optimised with int8 quantisation).
"""

import numpy as np
import logging

logger = logging.getLogger("athu.stt")


class SpeechToText:
    """
    Wraps faster-whisper for local speech recognition.
    Uses int8 quantisation for efficient CPU inference.
    Supported models: tiny.en, base.en, small.en, medium.en
    """

    def __init__(self, model_size: str = "base.en"):
        self.model_size = model_size
        self._model = None
        self._load()

    def _load(self):
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                download_root="data/models/whisper",
            )
            logger.info(f"Whisper STT loaded: {self.model_size}")
        except Exception as e:
            logger.error(f"Failed to load Whisper model '{self.model_size}': {e}")
            self._model = None

    def transcribe(self, audio: np.ndarray) -> str | None:
        """
        Transcribe audio to text.
        audio: float32 numpy array, normalised [-1.0, 1.0], 16kHz mono
        Returns: transcribed text or None on failure
        """
        if self._model is None:
            return None
        try:
            segments, info = self._model.transcribe(
                audio,
                language="en",
                beam_size=3,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(seg.text for seg in segments).strip()
            if text:
                logger.debug(f"Transcribed ({info.language}, {info.duration:.1f}s): {text!r}")
            return text or None
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None

    @property
    def is_available(self) -> bool:
        return self._model is not None

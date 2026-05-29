"""
ATHU Voice - Wake Word Detection
Uses OpenWakeWord with the hey_jarvis model (ONNX, local, free).
"""

import numpy as np
import logging

logger = logging.getLogger("athu.wake_word")


class WakeWordDetector:
    """
    Wraps OpenWakeWord for wake word detection.
    Processes 80ms audio chunks (1280 samples at 16kHz).
    Falls back to None if model is unavailable.
    """

    DETECTION_THRESHOLD = 0.5

    def __init__(self, wake_word: str = "hey_jarvis"):
        self.wake_word = wake_word
        self._model = None
        self._load()

    def _load(self):
        try:
            from openwakeword.model import Model
            self._model = Model(wakeword_models=[self.wake_word], inference_framework="onnx")
            logger.info(f"OpenWakeWord loaded: {self.wake_word}")
        except Exception as e:
            logger.warning(
                f"OpenWakeWord unavailable ({e}). "
                "Wake word disabled — ATHU will process all audio input."
            )
            self._model = None

    def detect(self, audio_chunk: np.ndarray) -> bool:
        """
        Returns True if the wake word is detected in the chunk.
        audio_chunk: int16 numpy array, 1280 samples (80ms @ 16kHz)
        """
        if self._model is None:
            return False
        try:
            audio_float = audio_chunk.astype(np.float32) / 32767.0
            predictions = self._model.predict(audio_float)
            for model_name, score in predictions.items():
                if score > self.DETECTION_THRESHOLD:
                    logger.debug(f"Wake word '{model_name}' score: {score:.3f}")
                    return True
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
        return False

    @property
    def is_available(self) -> bool:
        return self._model is not None

"""
ATHU Voice - Audio Pipeline
sounddevice circular buffer -> OpenWakeWord -> faster-whisper STT -> callback
"""

import threading
import queue
import logging
import asyncio
import numpy as np

logger = logging.getLogger("athu.audio")


class AudioPipeline:
    """
    Continuous audio pipeline running in a dedicated thread.
    Listens for the wake word, then captures speech until silence,
    transcribes it, and calls the async on_transcript callback.
    """

    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_SIZE = 1280    # 80ms at 16kHz (OpenWakeWord requirement)
    SILENCE_THRESHOLD = 200     # RMS amplitude below this = silence
    SILENCE_FRAMES = 25         # ~2 seconds of consecutive silence chunks
    MAX_RECORD_FRAMES = 375     # ~30 seconds max recording

    def __init__(self, config: dict, on_transcript: callable):
        self.config = config
        self.on_transcript = on_transcript
        self._audio_queue: queue.Queue = queue.Queue(maxsize=200)
        self._is_running = False
        self._listen_thread: threading.Thread | None = None
        self._stream = None
        self._event_loop: asyncio.AbstractEventLoop | None = None

        self._wake_word = None
        self._stt = None
        self._tts = None

    def _lazy_load_models(self):
        """Load models on first use to avoid blocking startup."""
        from voice.wake_word import WakeWordDetector
        from voice.stt import SpeechToText
        from voice.tts import TextToSpeech

        if self._wake_word is None:
            self._wake_word = WakeWordDetector(self.config["voice"]["wake_word"])
        if self._stt is None:
            self._stt = SpeechToText(self.config["voice"]["stt_model"])
        if self._tts is None:
            self._tts = TextToSpeech(self.config["voice"].get("tts_voice", "en_GB-alan-medium"))

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.debug(f"Audio status: {status}")
        try:
            audio_chunk = (indata[:, 0] * 32767).astype(np.int16)
            self._audio_queue.put_nowait(audio_chunk.copy())
        except queue.Full:
            pass  # Drop frame if queue is full

    def _listen_loop(self):
        """Dedicated thread: processes audio queue, detects wake word, captures utterances."""
        self._lazy_load_models()
        logger.info("Audio listen loop started. Waiting for wake word...")

        recording_buffer = []
        is_recording = False
        silence_frames = 0

        while self._is_running:
            try:
                chunk = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if not is_recording:
                if self._wake_word and self._wake_word.detect(chunk):
                    logger.info("Wake word detected!")
                    is_recording = True
                    recording_buffer = []
                    silence_frames = 0
                    self._tts.speak_async("Yes, Sir?")
            else:
                recording_buffer.append(chunk)
                amplitude = np.abs(chunk).mean()

                if amplitude < self.SILENCE_THRESHOLD:
                    silence_frames += 1
                else:
                    silence_frames = 0

                if (silence_frames >= self.SILENCE_FRAMES or
                        len(recording_buffer) > self.MAX_RECORD_FRAMES):
                    is_recording = False

                    if len(recording_buffer) > 3:  # Ignore blips < 240ms
                        audio_data = (
                            np.concatenate(recording_buffer).astype(np.float32) / 32767.0
                        )
                        transcript = self._stt.transcribe(audio_data)
                        if transcript and transcript.strip():
                            logger.info(f"Transcript: {transcript!r}")
                            if self._event_loop:
                                asyncio.run_coroutine_threadsafe(
                                    self.on_transcript(transcript.strip()),
                                    self._event_loop,
                                )

    def start(self, event_loop: asyncio.AbstractEventLoop):
        import sounddevice as sd
        self._event_loop = event_loop
        self._is_running = True

        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            dtype="float32",
            blocksize=self.CHUNK_SIZE,
            callback=self._audio_callback,
            device=self.config["voice"].get("input_device"),
        )
        self._stream.start()

        self._listen_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="athu-audio"
        )
        self._listen_thread.start()
        logger.info("Audio pipeline started.")

    def stop(self):
        self._is_running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
        logger.info("Audio pipeline stopped.")

    def speak(self, text: str):
        """Speak a response (non-blocking)."""
        if self._tts:
            self._tts.speak_async(text)
        else:
            logger.info(f"TTS not loaded. Would say: {text}")

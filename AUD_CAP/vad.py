
import numpy as np
from config import SILENCE_TIMEOUT_MS

class VADGate:
    def __init__(self, frame_ms, rms_threshold=500):
        self.frame_ms = frame_ms
        self.rms_threshold = rms_threshold
        self.silence_ms = 0

    def is_speech(self, frame_bytes):
        pcm = np.frombuffer(frame_bytes, dtype=np.int16)
        rms = np.sqrt(np.mean(pcm.astype(np.float32) ** 2))
        print(f"VAD RMS: {rms}")
        
        if rms > self.rms_threshold:
            self.silence_ms = 0
            return True
        else:
            self.silence_ms += self.frame_ms
            return False

    def is_timeout(self):
        return self.silence_ms > SILENCE_TIMEOUT_MS

    def reset(self):
        self.silence_ms = 0

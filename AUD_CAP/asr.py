import json
from vosk import Model, KaldiRecognizer
from config import SAMPLE_RATE, VOSK_MODEL_PATH
import sys


class ASR:
    def __init__(self):
        
        print("Attempting to load model...")
        
        self.model = Model(VOSK_MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.recognizer.SetWords(True)
        
        print("Model loaded successfully.")

    def reset(self):
        self.recognizer.Reset()

    def accept(self, frame_bytes):
        self.recognizer.AcceptWaveform(frame_bytes)

    def finalize(self):
        result = json.loads(self.recognizer.FinalResult())
        return result.get("text", "")



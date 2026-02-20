import queue
import sounddevice as sd
from config import SAMPLE_RATE, CHANNELS, DTYPE

audio_q = queue.Queue(maxsize=50)


def audio_callback(indata, frames, t, status):
    if status:
        pass
    try:
        audio_q.put_nowait(bytes(indata))
    except queue.Full:
        pass


class AudioInput:
    def __init__(self, blocksize=8000):
        self.blocksize = blocksize
        self.stream = None

    def start(self):
        if self.stream is not None:
            return

        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=self.blocksize,
            callback=audio_callback,
            latency="low",
        )
        
        print("starting audio stream")
        self.stream.start()
        print("started audio stream")
        
    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("stopped audio stream")

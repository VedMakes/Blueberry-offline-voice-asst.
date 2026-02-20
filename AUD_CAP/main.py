import time
import json
import numpy as np
import queue
from audio import audio_q, AudioInput
from wakeword import WakeWordDetector
from vad import VADGate
from asr import ASR
from mqtt_client import MQTTClient 
from config import SAMPLE_RATE

def run(): 
    mqtt = MQTTClient()
    mqtt.connect()  
    
    wake = WakeWordDetector()
    frame_len = wake.frame_length
    frame_ms = int(frame_len / SAMPLE_RATE * 1000)
    vad = VADGate(frame_ms)
    asr = ASR()
    
    print("Assistant started, waiting for wake word")
    
    try:
        while True:
            try:
                pcm = audio_q.get(timeout=1)
            except queue.Empty:
                continue
            
            pcm_np = np.frombuffer(pcm, dtype=np.int16)
            for i in range(0, len(pcm_np), frame_len):
                frame = pcm_np[i:i + frame_len]
                if len(frame) < frame_len:
                    continue
                
                try:
                    if wake.detect(frame):
                        print("\n Wake word detected!")
                        asr.reset()
                        vad.reset()
                        
                        # Publish wake word event
                        mqtt.client.publish("system/status", json.dumps({
                            "event": "wake_word_detected",
                            "timestamp": time.time()
                        }))
                        
                        while True:
                            try:
                                pcm2 = audio_q.get(timeout=5)
                            except queue.Empty:
                                print("Timeout waiting for command")
                                break
                            
                            pcm2_np = np.frombuffer(pcm2, dtype=np.int16)
                            for j in range(0, len(pcm2_np), frame_len):
                                f = pcm2_np[j:j + frame_len]
                                if len(f) < frame_len:
                                    continue
                                
                                try:
                                    asr.accept(f.tobytes())
                                    vad.is_speech(f.tobytes())
                                except Exception as e:
                                    print(f"ASR/VAD error: {e}")
                                    break
                                
                                if vad.is_timeout():
                                    text = asr.finalize()
                                    print(f"Recognized: {text}")
                                    
                                    if text.strip():
                                        # Send via MQTT (synchronous)
                                        success = mqtt.send_text(text)
                                        if success:
                                            print("Sent to MQTT")
                                    break
                            else:
                                continue
                            break
                        
                        print("Command processing complete, resuming wake word detection")
                        print("─" * 50)
                        
                except Exception as e:
                    print(f"Wake word processing error: {e}")
                    import traceback
                    traceback.print_exc()
                    
    except Exception as e:
        print(f"FATAL ERROR in main loop: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        mqtt.disconnect()

def main():
    audio = AudioInput()
    audio.start()
    try:
        run()  # No asyncio.run() needed
    except KeyboardInterrupt:
        print("\n Interrupted by user")
    except Exception as e:
        print(f"Main exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Stopping audio...")
        audio.stop()
        print("Cleanup complete")

if __name__ == "__main__":
    main()
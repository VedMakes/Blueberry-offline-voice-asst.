

import subprocess
import os
import hashlib
import wave
from pathlib import Path
from typing import Optional
import time
import unicodedata
import re

class TTSEngine:
    def __init__(
        self,
        model_path="models/hi_IN-rohan-medium.onnx",
        speaker_id=0,
        cache_dir="tts_cache",
        sample_rate=22050,
        json_path="models/hi_IN-rohan-medium.onnx.json"
    ):
        """
        Initialize TTS engine
        
        Args:
            model_path: Path to Piper ONNX model
            speaker_id: Voice ID (if model supports multiple speakers)
            cache_dir: Directory for caching synthesized audio
            sample_rate: Output sample rate
        """
        self.model_path = model_path
        self.speaker_id = speaker_id
        self.sample_rate = sample_rate
        self.config_path = json_path
        
        # Setup cache
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Verify Piper is installed
        # if not self._check_piper():
        #     raise Exception("Piper TTS not found. Install: pip install piper-tts")
        
        print(f"✓ TTS Engine initialized")
        print(f"  Model: {model_path}")
        print(f"  Cache: {cache_dir}")
    
    def _check_piper(self) -> bool:
        """Check if Piper is available"""
        try:
            result = subprocess.run(
                ["piper", "--version"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False
    
    def _clean_text(self, text: str) -> str:
        # Normalize unicode
        text = unicodedata.normalize("NFC", text)

        # Remove zero-width characters
        text = text.replace("\u200c", "")
        text = text.replace("\u200d", "")

        # Remove non-breaking space
        text = text.replace("\u00a0", " ")

        # Optional: remove unsupported punctuation
        text = re.sub(r"[^\u0900-\u097F0-9a-zA-Z\s.,!?]", "", text)
    
        text = unicodedata.normalize("NFC", text)

        text = text.encode("utf-8", "ignore").decode("utf-8")

        return text.strip()
    
    def synthesize(self, text: str, output_path: Optional[str] = None) -> str:
        """
        Synthesize speech from text
        
        Args:
            text: Text to speak
            output_path: Optional output file path (generated if None)
        
        Returns:
            Path to generated audio file
        """
        text = self._clean_text(text)
        if not text:
            print("✗ Empty or invalid text")
            return None
        
        start = time.time()
        
        print([hex(ord(c)) for c in text])
        # Check cache first
        cache_key = self._get_cache_key(text)
        cached_path = self.cache_dir / f"{cache_key}.wav"
        
        if cached_path.exists():
            print(f"✓ TTS cache hit ({(time.time() - start) * 1000:.0f}ms)")
            return str(cached_path)
        
        # Generate output path
        if not output_path:
            output_path = cached_path
        
        # Run Piper TTS
        try:
            cmd = [
                "piper",
                "--model", self.model_path,
                "--output_file", str(output_path),
            ]
            
            # Add speaker ID if supported
            if self.speaker_id is not None:
                cmd.extend(["--speaker", str(self.speaker_id)])
            
            # Run synthesis
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            stdout, stderr = process.communicate(
                input=text.encode("utf-8"),
                timeout=5
            )
            
            if process.returncode != 0:
                print(f"TTS error: {stderr}")
                return None
            
            elapsed = (time.time() - start) * 1000
            print(f"✓ TTS synthesized ({elapsed:.0f}ms)")
            
            return str(output_path)
        
        except Exception as e:
            print(f"TTS synthesis failed: {e}")
            return None
    
    def synthesize_stream(self, text: str) -> bytes:
        """
        Synthesize and return raw audio bytes
        Useful for streaming or MQTT
        
        Returns:
            Raw PCM audio bytes
        """
        # Synthesize to temp file
        audio_path = self.synthesize(text)
        
        if not audio_path:
            return None
        
        # Read audio file
        try:
            with wave.open(audio_path, 'rb') as wf:
                return wf.readframes(wf.getnframes())
        except Exception as e:
            print(f"Failed to read audio: {e}")
            return None
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        # Create hash of text + speaker_id
        content = f"{text}_{self.speaker_id}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear TTS cache"""
        for file in self.cache_dir.glob("*.wav"):
            file.unlink()
        print("✓ TTS cache cleared")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        files = list(self.cache_dir.glob("*.wav"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            'cached_files': len(files),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }
    
    def pregenerate_common_phrases(self):
        """Pre-generate common responses for instant playback"""
        common_phrases = [
            "ठीक है",
            "हो गया",
            "मुझे समझ नहीं आया",
            "कुछ गड़बड़ हो गई",
            "और कुछ?",
            "नमस्ते! मैं आपकी कैसे मदद कर सकता हूं?",
            "अलविदा! अच्छा दिन हो।",
            "किचन की लाइट चालू कर दी",
            "बेडरूम का पंखा बंद कर दिया",
            "अलार्म सेट कर दिया",
            "टाइमर शुरू कर दिया",
        ]
        
        print("Pre-generating common phrases...")
        for phrase in common_phrases:
            self.synthesize(phrase)
        
        print(f"✓ Pre-generated {len(common_phrases)} phrases")


# ==================== AUDIO PLAYBACK ====================

class AudioPlayer:
    """Simple audio playback using system tools"""
    
    @staticmethod
    def play(audio_path: str):
        """Play audio file"""
        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")
            return
        
        try:
            # Try different playback methods based on OS
            if os.name == 'nt':  # Windows
                import winsound
                winsound.PlaySound(audio_path, winsound.SND_FILENAME)
            else:  # Linux/Mac
                subprocess.run(
                    ["aplay", "-q", audio_path],
                    check=True,
                    timeout=10
                )
        except Exception as e:
            print(f"Playback failed: {e}")


# ==================== MQTT INTEGRATION ====================

def mqtt_tts_handler(mqtt_client, tts_engine: TTSEngine, audio_player: AudioPlayer):
    """
    MQTT message handler for TTS requests
    
    Subscribe to: rasa/response/text
    Synthesize and play audio
    """
    def on_message(client, userdata, msg):
        if msg.topic == "tts/speak":
            text = msg.payload.decode('utf-8')
            print(f"🔊 Speaking: {text}")
            
            # Synthesize
            audio_path = tts_engine.synthesize(text)
            
            if audio_path:
                # Play audio
                audio_player.play(audio_path)
                
                # Publish completion event
                client.publish("tts/complete", "done")
    
    mqtt_client.message_callback_add("tts/speak", on_message)
    mqtt_client.subscribe("tts/speak")


# ==================== STANDALONE TEST ====================

if __name__ == "__main__":
    print("=" * 60)
    print("TTS Engine Test")
    print("=" * 60)
    
    # Initialize
    tts = TTSEngine()
    player = AudioPlayer()
    
    # Pre-generate common phrases
    tts.pregenerate_common_phrases()
    
    # Test phrases
    test_phrases = [
        "नमस्ते! मैं आपकी कैसे मदद कर सकता हूं?",
        "किचन की लाइट चालू कर दी",
        "7 बजे का अलार्म सेट कर दिया",
        "ठीक है",
    ]
    
    print("\n" + "=" * 60)
    print("Testing TTS")
    print("=" * 60)
    
    for phrase in test_phrases:
        print(f"\nSynthesizing: {phrase}")
        audio_path = tts.synthesize(phrase)
        
        if audio_path:
            print(f"  Output: {audio_path}")
            # Uncomment to play:
            # player.play(audio_path)
    
    # Cache stats
    print("\n" + "=" * 60)
    stats = tts.get_cache_stats()
    print(f"Cache: {stats['cached_files']} files, {stats['total_size_mb']:.2f} MB")
    print("=" * 60)

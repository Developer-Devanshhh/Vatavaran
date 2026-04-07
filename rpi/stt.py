"""
Raspberry Pi Speech-to-Text Module

Uses Vosk for on-device speech recognition.
Requirements: 2.1, 2.2, 2.3, 2.4, 12.4
"""

import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Vosk model path
MODEL_PATH = Path.home() / 'vatavaran' / 'vosk-model-small-en-in-0.4'

def transcribe_audio(audio_file=None, duration=5):
    """
    Transcribe audio to text using Vosk.
    
    Args:
        audio_file: Path to audio file (optional, will record if None)
        duration: Recording duration in seconds (default 5)
    
    Returns:
        str: Transcribed text, or None on error
    
    Requirements:
        2.1: Record audio for 5 seconds after button press or wake word
        2.2: Transcribe audio to text using on-device processing (Vosk)
        2.3: Return plain text string without cloud connectivity
        2.4: Return error indicator on transcription failure
    """
    try:
        # Check if Vosk is installed
        try:
            from vosk import Model, KaldiRecognizer
            import pyaudio
            import wave
        except ImportError:
            logger.error("Vosk or PyAudio not installed. Install with: pip install vosk pyaudio")
            return None
        
        # Check if model exists
        if not MODEL_PATH.exists():
            logger.error(f"Vosk model not found at {MODEL_PATH}")
            logger.info("Download model from: https://alphacephei.com/vosk/models")
            logger.info(f"Extract to: {MODEL_PATH}")
            return None
        
        # Load Vosk model
        logger.info(f"Loading Vosk model from {MODEL_PATH}")
        model = Model(str(MODEL_PATH))
        recognizer = KaldiRecognizer(model, 16000)
        
        if audio_file:
            # Transcribe from file
            logger.info(f"Transcribing from file: {audio_file}")
            with wave.open(audio_file, 'rb') as wf:
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    recognizer.AcceptWaveform(data)
        else:
            # Requirement 2.1: Record audio for 5 seconds
            logger.info(f"Recording audio for {duration} seconds...")
            
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8000
            )
            stream.start_stream()
            
            # Record for specified duration
            frames_to_record = int(16000 / 8000 * duration)
            for _ in range(frames_to_record):
                data = stream.read(8000)
                recognizer.AcceptWaveform(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            logger.info("Recording complete")
        
        # Requirement 2.2, 2.3: Get transcription result (on-device, no cloud)
        result = json.loads(recognizer.FinalResult())
        text = result.get('text', '').strip()
        
        if text:
            logger.info(f"Transcribed: '{text}'")
            return text
        else:
            # Requirement 2.4: Return error indicator on empty output
            logger.warning("Transcription produced empty output")
            return None
            
    except Exception as e:
        # Requirement 2.4: Return error indicator on transcription failure
        logger.error(f"Transcription failed: {e}")
        return None

def wait_for_trigger():
    """
    Wait for button press or wake word detection.
    
    Returns:
        bool: True if triggered, False on error
    """
    # TODO: Implement button press detection or wake word
    # For button: Use GPIO library
    # For wake word: Use Porcupine or similar
    
    logger.info("Waiting for trigger (button press or wake word)...")
    
    # Placeholder: Return True immediately for testing
    # In production, wait for actual trigger
    return True

def main():
    """Main entry point for STT module"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Vatavaran Speech-to-Text Module")
    print("=" * 50)
    
    # Wait for trigger
    if not wait_for_trigger():
        print("Trigger failed")
        return 1
    
    # Transcribe audio
    text = transcribe_audio(duration=5)
    
    if text:
        print(f"\nTranscribed: '{text}'")
        return 0
    else:
        print("\nTranscription failed")
        return 1

if __name__ == "__main__":
    exit(main())

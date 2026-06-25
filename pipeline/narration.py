import os
from openai import OpenAI
from typing import Optional

class NarrationEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def generate_audio(self, text: str, output_path: str, voice: str = "onyx") -> str:
        """
        Generates audio from text using OpenAI TTS.
        """
        if not self.client:
            print("Warning: No OpenAI API key provided. Using placeholder audio.")
            return self._generate_placeholder(output_path)

        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            response.stream_to_file(output_path)
            print(f"Audio generated: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error generating audio: {e}")
            return self._generate_placeholder(output_path)

    def _generate_placeholder(self, output_path: str) -> str:
        # Create a dummy silent audio file using moviepy
        from moviepy import AudioClip
        import numpy as np
        
        duration = 10
        def make_frame(t):
            return np.sin(2 * np.pi * 440 * t) * 0.01
            
        audio = AudioClip(make_frame, duration=duration, fps=44100)
        
        # If output_path is .mp3 and we want to use wav for placeholder
        if output_path.endswith('.mp3'):
            actual_path = output_path.replace('.mp3', '.wav')
        else:
            actual_path = output_path
            
        audio.write_audiofile(actual_path, fps=44100, logger=None)
        return actual_path

def generate_narration(script_file, output_audio):
    """
    Reads the script and generates a full narration audio file.
    Returns the path to the generated audio file.
    """
    if not os.path.exists(os.path.dirname(output_audio)):
        os.makedirs(os.path.dirname(output_audio), exist_ok=True)

    with open(script_file, 'r') as f:
        script_text = f.read()
    
    engine = NarrationEngine()
    return engine.generate_audio(script_text[:4000], output_audio)

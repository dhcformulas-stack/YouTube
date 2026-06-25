import os
import re
from openai import OpenAI
from typing import Optional

class AssetGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def generate_image(self, prompt: str, output_path: str) -> str:
        """
        Generates an image using DALL-E 3.
        """
        if not self.client:
            print(f"Warning: No OpenAI API key provided. Using placeholder for: {prompt}")
            return self._generate_placeholder(output_path)

        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            
            # Download the image
            import requests
            img_data = requests.get(image_url).content
            with open(output_path, 'wb') as handler:
                handler.write(img_data)
            
            print(f"Image generated and saved: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error generating image: {e}")
            return self._generate_placeholder(output_path)

    def _generate_placeholder(self, output_path: str) -> str:
        from PIL import Image
        img = Image.new('RGB', (1280, 720), color = (73, 109, 137))
        img.save(output_path)
        return output_path

def generate_assets(script_file, output_dir):
    """
    Parses the script for [Visual: ...] cues and generates images.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(script_file, 'r') as f:
        script_content = f.read()
    
    # Extract visual cues
    visual_cues = re.findall(r'\[Visual: (.*?)\]', script_content)
    
    generator = AssetGenerator()
    
    for i, cue in enumerate(visual_cues):
        output_path = os.path.join(output_dir, f"scene_{i+1}.png")
        generator.generate_image(cue, output_path)

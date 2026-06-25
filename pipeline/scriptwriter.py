import os
from openai import OpenAI
from typing import Optional

class ScriptEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def generate_script(self, research_data: str, target_duration_mins: int = 30) -> str:
        """
        Generates a documentary script using GPT-4o.
        """
        if not self.client:
            print("Warning: No OpenAI API key provided. Using placeholder script.")
            return self._generate_placeholder()

        prompt = f"""
        You are a professional documentary scriptwriter. 
        Based on the following research data, write a {target_duration_mins}-minute documentary script.
        
        Structure the script with:
        - Compelling Hooks
        - Introduction
        - 3-4 Deep-dive Chapters
        - Conclusion
        
        Include [Visual: ...] tags for scene descriptions that will be used for AI image generation. 
        There should be at least 20-30 such tags throughout the script to ensure a dynamic visual experience.
        
        Narrator voice should be engaging and informative.
        
        Research Data:
        {research_data}
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a world-class documentary filmmaker."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating script: {e}")
            return self._generate_placeholder()

    def _generate_placeholder(self) -> str:
        return "# Documentary Script\n\n[Visual: A placeholder landscape]\nNarrator: This is a placeholder script because the AI engine was not available."

def write_script(research_file, output_path):
    """
    Generates a script based on the research file.
    """
    with open(research_file, 'r') as f:
        research_data = f.read()
    
    engine = ScriptEngine()
    script_content = engine.generate_script(research_data)
    
    with open(output_path, 'w') as f:
        f.write(script_content)
    
    print(f"Script saved to {output_path}")

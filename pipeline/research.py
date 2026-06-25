import os
from openai import OpenAI
from typing import Optional

class ResearchEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def conduct_research(self, topic: str) -> str:
        """
        Gathers facts about a topic.
        """
        if not self.client:
            print(f"Warning: No OpenAI API key provided. Using basic research for: {topic}")
            return f"Topic: {topic}\n\nFacts: {topic} is a fascinating subject with many historical and scientific details."

        prompt = f"""
        Conduct deep research on the following topic for a 30-minute documentary:
        {topic}
        
        Provide a comprehensive report including:
        - Key historical events
        - Scientific principles
        - Major figures involved
        - Current understanding/consensus
        - Controversies or unresolved questions
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a thorough historical and scientific researcher."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error conducting research: {e}")
            return f"Research failed for {topic}."

def conduct_research(topic, output_path):
    """
    Conducts research on the topic and saves it to a file.
    """
    engine = ResearchEngine()
    research_data = engine.conduct_research(topic)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(research_data)
    
    print(f"Research saved to {output_path}")

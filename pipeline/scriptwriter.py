import os

def write_script(research_file, output_path):
    """
    Generates a script based on the research file.
    """
    with open(research_file, 'r') as f:
        research_data = f.read()
    
    # Placeholder for script generation logic
    script_content = f"""# Documentary Script

## Hook (0:00 - 2:00)
[Visual: Compelling intro image]
Narrator: Welcome to this deep dive into {research_file}...

## Introduction (2:00 - 5:00)
...

## Chapter 1: Foundations (5:00 - 12:00)
...

## Chapter 2: The Core (12:00 - 22:00)
...

## Chapter 3: Legacy (22:00 - 28:00)
...

## Conclusion (28:00 - 30:00)
...
"""
    with open(output_path, 'w') as f:
        f.write(script_content)
    print(f"Script saved to {output_path}")

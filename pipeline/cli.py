import click
import os
from pipeline.research import conduct_research
from pipeline.scriptwriter import write_script
from pipeline.assets import generate_assets
from pipeline.assembly import assemble_video
from pipeline.fact_checker import verify_claims
from pipeline.narration import generate_narration

@click.group()
def cli():
    pass

@cli.command()
@click.argument('topic')
@click.option('--output', default='output/research.md', help='Output file for research')
def research(topic, output):
    conduct_research(topic, output)

@cli.command()
@click.argument('research_file')
@click.option('--output', default='output/script.md', help='Output file for script')
def script(research_file, output):
    write_script(research_file, output)

@cli.command()
@click.argument('script_file')
@click.option('--output', default='output/narration.mp3', help='Output file for narration')
def narrate(script_file, output):
    actual_path = generate_narration(script_file, output)
    print(f"Narration generated at: {actual_path}")

@cli.command()
@click.argument('script_file')
@click.option('--output-dir', default='output/assets', help='Directory for generated assets')
def assets(script_file, output_dir):
    generate_assets(script_file, output_dir)

@cli.command()
@click.argument('asset_dir')
@click.argument('script_file')
@click.argument('audio_file')
@click.option('--output', default='output/final_video.mp4', help='Final video file')
def assemble(asset_dir, script_file, audio_file, output):
    # If audio_file doesn't exist but a .wav version does (placeholder fallback)
    if not os.path.exists(audio_file) and os.path.exists(audio_file.replace('.mp3', '.wav')):
        audio_file = audio_file.replace('.mp3', '.wav')
        
    assemble_video(asset_dir, script_file, audio_file, output)

@cli.command()
@click.argument('script_file')
@click.argument('research_file')
def verify(script_file, research_file):
    if verify_claims(script_file, research_file):
        print("Fact-check passed!")
    else:
        print("Fact-check failed!")

if __name__ == '__main__':
    cli()

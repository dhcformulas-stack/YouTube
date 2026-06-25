# Chronicle Forge Video Production Pipeline

This repository contains the core pipeline for producing 30-minute documentary videos.

## Structure
- `pipeline/`: Core Python modules for research, scriptwriting, asset generation, and assembly.
- `templates/`: Markdown templates for research documents and scripts.
- `docs/`: Workflow documentation.

## Usage
1. Set up a virtual environment: `python3 -m venv venv && source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the CLI: `export PYTHONPATH=$PYTHONPATH:. && python3 pipeline/cli.py --help`

See `docs/workflow.md` for more details.

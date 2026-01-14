"""Entry point for the AI Agent Orchestration System."""

import os
import sys
from cli.interface import cli

def main():
    """Main entry point."""
    # Ensure necessary directories exist
    os.makedirs('data/outputs/state', exist_ok=True)
    os.makedirs('data/sample_inputs', exist_ok=True)
    
    # Run the CLI
    cli()

if __name__ == "__main__":
    main()

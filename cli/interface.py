"""CLI commands and interface for EntraFlow."""

import click
import json
import os
from pprint import pprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from orchestrator.orchestrator import Orchestrator
from utils.config import Config
from utils.exceptions import OrchestratorError, AgentError

console = Console()


@click.group()
def cli():
    """EntraFlow: AI Agent Orchestration System CLI"""
    pass


@cli.command()
@click.option('--workflow', '-w', default='enterprise_analysis', help='Workflow name to run')
@click.option('--location', '-l', default='London', help='Location for data fetcher')
@click.option('--query', '-q', default='AI technology', help='News query for data fetcher')
def run(workflow, location, query):
    """Run a complete agent workflow"""
    try:
        config = Config()
        orchestrator = Orchestrator(config)
        
        console.print(Panel(f"Running Workflow: [bold cyan]{workflow}[/bold cyan]", title="Execution Start", border_style="bold magenta"))
        
        initial_inputs = {
            'location': location,
            'news_query': query
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            # This is a simulation since execute_workflow is synchronous
            main_task = progress.add_task(f"Executing {workflow}...", total=100)
            
            # In a real scenario, we might use callbacks or a thread to update progress
            # For this demo, we'll just run it and update after
            result = orchestrator.execute_workflow(workflow, initial_inputs)
            progress.update(main_task, completed=100)
            
        _display_workflow_result(result)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.option('--agent', '-a', required=True, help='Agent name to test')
@click.option('--input-file', '-i', type=click.Path(exists=True), help='JSON file containing agent inputs')
def test(agent, input_file):
    """Test an individual agent in standalone mode"""
    try:
        config = Config()
        orchestrator = Orchestrator(config)
        
        inputs = {}
        if input_file:
            with open(input_file, 'r') as f:
                inputs = json.load(f)
        
        console.print(f"Testing Agent: [bold yellow]{agent}[/bold yellow]")
        result = orchestrator.execute_agent_standalone(agent, inputs)
        
        console.print(Panel(json.dumps(result, indent=2), title="Agent Result", border_style="green"))
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
def status():
    """Check the status of all agents"""
    try:
        config = Config()
        orchestrator = Orchestrator(config)
        statuses = orchestrator.get_agent_status()
        
        table = Table(title="Agent Status")
        table.add_column("Agent Name", style="cyan")
        table.add_column("Executions", justify="right")
        table.add_column("Last Exec Time (s)", justify="right")
        table.add_column("Status", style="green")
        
        for name, state in statuses.items():
            table.add_row(
                name,
                str(state['execution_count']),
                f"{state['last_execution_time']:.2f}" if state['last_execution_time'] else "N/A",
                "Ready"
            )
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
def list_workflows():
    """List all available workflows"""
    try:
        config = Config()
        orchestrator = Orchestrator(config)
        workflows = orchestrator.list_workflows()
        
        table = Table(title="Available Workflows")
        table.add_column("Name", style="bold magenta")
        table.add_column("Description")
        
        for name in workflows:
            desc = orchestrator.get_workflow_info(name).get('description', '')
            table.add_row(name, desc)
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


def _display_workflow_result(result):
    """Helper to display workflow execution results nicely"""
    status = result.get('status', 'unknown')
    color = "green" if status == "completed" else "red"
    
    # Executive Summary Extraction
    outputs = result.get('outputs', {})
    summary = "No summary available"
    
    # Try to find a summary in known output keys
    # We prefer validated_report (Supervisor) -> report (Notifier) -> others
    for key in ['validated_report', 'report', 'notifier_output']:
        if key in outputs and isinstance(outputs[key], dict):
            # Check for various summary field names
            for s_key in ['supervisor_summary', 'summary', 'executive_summary']:
                if outputs[key].get(s_key):
                    summary = outputs[key][s_key]
                    break
            if summary != "No summary available":
                break
    
    console.print(Panel(summary, title="[bold]Workflow Summary[/bold]", border_style=color))
    
    # Workflow Metadata
    meta_table = Table(title="Execution Metadata", box=None)
    meta_table.add_column("Key", style="dim")
    meta_table.add_column("Value")
    
    meta_table.add_row("Status", f"[{color}]{status.upper()}[/{color}]")
    meta_table.add_row("Duration", f"{result.get('execution_time', 0):.2f}s")
    meta_table.add_row("Completed Agents", ", ".join(result.get('completed_agents', [])))
    
    if result.get('state_file'):
        meta_table.add_row("State File", result['state_file'])
        
    console.print(meta_table)


if __name__ == '__main__':
    cli()

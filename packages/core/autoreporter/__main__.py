"""CLI entry point for Auto-Reporter."""

import os
import sys
from datetime import datetime

import click
from rich.console import Console
from rich.markdown import Markdown

from .slack_client import SlackClient
from .aggregator import MessageAggregator
from .reporter import ReportGenerator


console = Console()


@click.command()
@click.option('--channel', envvar='SLACK_CHANNEL_ID', help='Slack channel ID')
@click.option('--token', envvar='SLACK_BOT_TOKEN', help='Slack bot token')
@click.option('--days', default=1, help='Number of days to look back')
@click.option('--output', '-o', help='Output file path (optional)')
@click.option('--channel-name', default='channel', help='Channel name for display')
def main(channel, token, days, output, channel_name):
    """Generate Auto-Reporter status report from Slack channel."""
    try:
        console.print("[bold blue]Auto-Reporter[/bold blue] - Generating status report...")
        
        # Initialize clients
        client = SlackClient(token=token)
        aggregator = MessageAggregator()
        reporter = ReportGenerator()
        
        # Fetch messages
        console.print(f"Fetching messages from last {days} day(s)...")
        messages = client.get_channel_history(channel, days=days)
        console.print(f"Found {len(messages)} messages")
        
        # Aggregate and analyze
        console.print("Analyzing messages for action items, bugs, and blockers...")
        aggregated = aggregator.aggregate(messages)
        
        # Generate report
        console.print("Generating report...")
        report = reporter.generate(aggregated, channel_name=channel_name)
        
        # Output
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(report)
            console.print(f"[green]Report saved to {output}[/green]")
        else:
            console.print("\n")
            md = Markdown(report)
            console.print(md)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()

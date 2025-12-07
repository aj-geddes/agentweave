"""
AgentWeave SDK - CLI Utilities
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax


console = Console()


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load and parse configuration file.

    Args:
        config_path: Path to configuration file (YAML)

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    path = Path(config_path)

    if not path.exists():
        error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        with open(path) as f:
            config = yaml.safe_load(f)
        return config
    except yaml.YAMLError as e:
        error(f"Invalid YAML in configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        error(f"Error loading configuration: {e}")
        sys.exit(1)


def success(message: str):
    """Display success message."""
    console.print(f"[green]✓[/green] {message}")


def error(message: str):
    """Display error message."""
    console.print(f"[red]✗[/red] {message}", file=sys.stderr)


def warning(message: str):
    """Display warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def info(message: str):
    """Display info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_json(data: Any, title: Optional[str] = None):
    """
    Pretty print JSON data.

    Args:
        data: Data to print as JSON
        title: Optional title for the panel
    """
    json_str = json.dumps(data, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)

    if title:
        console.print(Panel(syntax, title=title, border_style="blue"))
    else:
        console.print(syntax)


def print_table(data: list, columns: list, title: Optional[str] = None):
    """
    Print data as a formatted table.

    Args:
        data: List of dictionaries to display
        columns: List of column names to display
        title: Optional table title
    """
    table = Table(title=title, show_header=True, header_style="bold blue")

    for column in columns:
        table.add_column(column.replace("_", " ").title())

    for row in data:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)


def print_key_value(data: Dict[str, Any], title: Optional[str] = None):
    """
    Print key-value pairs in a formatted way.

    Args:
        data: Dictionary of key-value pairs
        title: Optional title
    """
    table = Table(title=title, show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()

    for key, value in data.items():
        table.add_row(f"{key}:", str(value))

    console.print(table)


def validate_spiffe_id(spiffe_id: str) -> bool:
    """
    Validate SPIFFE ID format.

    Args:
        spiffe_id: SPIFFE ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not spiffe_id.startswith("spiffe://"):
        return False

    parts = spiffe_id[9:].split("/")
    if len(parts) < 1:
        return False

    # Trust domain (first part) must not be empty
    if not parts[0]:
        return False

    return True


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f}µs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        mins = int(seconds / 60)
        secs = seconds % 60
        return f"{mins}m {secs:.2f}s"


def format_bytes(bytes_count: int) -> str:
    """
    Format byte count in human-readable format.

    Args:
        bytes_count: Number of bytes

    Returns:
        Formatted byte string
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def confirm(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation.

    Args:
        message: Confirmation message
        default: Default value if user presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    default_str = "Y/n" if default else "y/N"
    response = console.input(f"[yellow]?[/yellow] {message} [{default_str}]: ").strip().lower()

    if not response:
        return default

    return response in ["y", "yes"]

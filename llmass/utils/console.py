from rich.console import Console

# Singleton console instance for the entire application
console = Console()


def prompt_user() -> str:
    q = console.input("[green]> [/green]")
    print()

    return q

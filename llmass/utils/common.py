from pathlib import Path
from collections.abc import Callable
from rich.panel import Panel

from llmass.utils.console import console


def get_project_path() -> Path:
    return Path(__file__).parent.parent.parent


def get_config_path() -> Path:
    return get_project_path() / "config"


def get_markdown_filenames(p: str, excluded_filenames: list[str]) -> list[str]:
    p = Path(p)
    md_files = list(map(lambda s: s.name, p.glob("*.md")))
    for excluded_filename in excluded_filenames:
        if excluded_filename in md_files:
            md_files.remove(excluded_filename)
    return md_files


def transform_filename_to_capitalized_name(f: str) -> str:
    return " ".join(map(lambda s: s.capitalize(), Path(f).stem.split("_")))


def prompt_until_satisfied(
    prompt_msg: str,
    input_prompt: str,
    msg_if_satisfied: str,
    msg_if_not_satisfied: str,
    condition: Callable[[str], bool],
) -> str:
    res = None
    while res is None:
        console.print(prompt_msg, style="green")
        res = console.input(f"[green]{input_prompt}[/green]")
        if condition(res):
            console.print(msg_if_satisfied, style="green")
            console.print()
        else:
            console.print(msg_if_not_satisfied, style="green")
            res = None

    return res


def print_llm_output(llm_output: str) -> None:
    console.print()
    console.print(Panel(llm_output, border_style="green"))
    console.print()


def to_boolean(llm_output: str) -> bool:
    s = llm_output.lower()
    if s.startswith("yes") or s.startswith("true"):
        return True
    elif s.startswith("no") or s.startswith("false"):
        return False

    raise ValueError(f"LLM output is inconsistent with the boolean type: '{s}'")
 

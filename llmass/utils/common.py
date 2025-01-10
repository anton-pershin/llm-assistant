from pathlib import Path
from collections.abc import Callable


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
        print(prompt_msg)
        res = input(input_prompt)
        if condition(res):
            print(msg_if_satisfied)
            print()
        else:
            print(msg_if_not_satisfied)
            res = None

    return res

from pathlib import Path
import random
from typing import Optional

from omegaconf import DictConfig
import feedparser
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import track

from llmass.utils.console import console, prompt_user

from llmass.interaction import (
    single_message_non_dialogue_interaction_with_llm,
    recurrent_non_dialogue_interaction_with_llm,
)
from llmass.utils.common import (
    get_markdown_filenames,
    transform_filename_to_capitalized_name,
    prompt_until_satisfied,
    print_llm_output,
    to_boolean,
)
from llmass.utils.markdown import MdParser


def warmup(cfg: DictConfig) -> None:
    _print_mode_title(warmup.__name__)
    _run_interaction_based_on_single_md_file(
        md_path=cfg.routine_path,
        prompts=cfg.prompts.warmup,
        llm_server_url=cfg.llm_server_url,
        stop_word=cfg.stop_word,
        ask_startup_question=True,
    )


def relax(cfg: DictConfig) -> None:
    _print_mode_title(relax.__name__)
    _run_interaction_based_on_single_md_file(
        md_path=cfg.relax_path,
        prompts=cfg.prompts.relax,
        llm_server_url=cfg.llm_server_url,
        stop_word=cfg.stop_word,
        ask_startup_question=False,
    )


def projects(project_path: str, cfg: DictConfig) -> None:
    _print_mode_title(projects.__name__)
    # Collect all the project files in the project dir
    project_md_files = []
    excluded_filenames = (
        "definitions.md",
    )
    project_path = Path(project_path)
    project_md_files = get_markdown_filenames(p=project_path, excluded_filenames=excluded_filenames)
    _print_list_with_numeric_options(title="projects", files_or_dirs=project_md_files)

    while True:
        md_file_i = prompt_until_satisfied(
            prompt_msg="Choose the file by its number",
            input_prompt="> ",
            msg_if_satisfied="Running LLM conversation regarding this project",
            msg_if_not_satisfied="Wrong number. Try again",
            condition=lambda i_as_str: 1 <= int(i_as_str) <= len(project_md_files),
        )
        md_file = project_md_files[int(md_file_i) - 1]

        with open(project_path / md_file, "r") as f:
            md_file_content = f.read()
            recurrent_non_dialogue_interaction_with_llm(
                llm_server_url=cfg.llm_server_url,
                system_prompt=cfg.prompts.project_management.system_prompt, 
                user_prompt_prefix=cfg.prompts.project_management.user_prompt_prefix,
                user_prompt_suffix=cfg.prompts.project_management.user_prompt_suffix,
                user_prompt_extra_content=md_file_content,
                stop_word=cfg.stop_word,
            )


def recent_papers(rss_feed_urls: list[str], output_filename: str, cfg: DictConfig) -> None:
    _print_mode_title(recent_papers.__name__)
    md_buf = ""
    already_processed_titles = set()
    for rss_i, rss_feed in enumerate(rss_feed_urls):
        feed = feedparser.parse(rss_feed["url"])
        if feed.status != 200:
            raise ValueError("Cannot get RSS feed, code: {feed.status}")

        for entry in track(feed.entries, description=f"RSS feed {rss_i + 1}/{len(rss_feed_urls)}: {rss_feed['name']}"):
            title = entry.title
            if title not in already_processed_titles:
                abstract = entry.description.split("\n")[1][10:]
                llm_output = single_message_non_dialogue_interaction_with_llm(
                    llm_server_url=cfg.llm_server_url,
                    system_prompt=cfg.prompts.recent_papers.system_prompt, 
                    user_prompt_prefix=cfg.prompts.recent_papers.user_prompt_prefix,
                    user_prompt_question=cfg.prompts.recent_papers.user_prompt_question_at_startup,
                    user_prompt_suffix=cfg.prompts.recent_papers.user_prompt_suffix,
                    user_prompt_extra_content=f"Title: {title}" + "\n" + f"Abstract: {abstract}" + "\n",
                )
                relevant = to_boolean(llm_output)
                if relevant:
                    md_buf += f"### {title}" 
                    md_buf += "\n\n" 
                    md_buf += f"**Link:** {entry.link}" 
                    md_buf += "\n\n" 
                    md_buf += f"**Abstract:** {abstract}"
                    md_buf += "\n\n" 
                    already_processed_titles.add(title)
                    
    with open(output_filename, "w") as f:
        f.write(md_buf)


def search(cfg: DictConfig) -> None:
    _print_mode_title(search.__name__)
    # First, let user choose the collection
    collections = list(cfg.markdown_collections.keys())
    _print_list_with_numeric_options(
        title="collections", 
        files_or_dirs=[cfg.markdown_collections[name].path for name in collections],
        names=[name for name in collections],
        descriptions=[cfg.markdown_collections[name].description for name in collections],
    )
    
    collection_i = prompt_until_satisfied(
        prompt_msg="Choose collection to search in by its number",
        input_prompt="> ",
        msg_if_satisfied="Good choice, buddy!",
        msg_if_not_satisfied="Wrong number. Try again",
        condition=lambda i_as_str: 1 <= int(i_as_str) <= len(collections),
    )
    selected_collection = collections[int(collection_i) - 1]
    collection_path = Path(cfg.markdown_collections[selected_collection].path)

    # Get query from user
    console.print("[green]Enter your search query:[/green]")
    query = prompt_user()
    
    # Get all markdown files recursively from selected collection
    excluded_filenames = ("definitions.md",)
    md_files = []
    for f in collection_path.rglob("*.md"):
        if f.name not in excluded_filenames:
            md_files.append(str(f.relative_to(collection_path)))
    
    results = []
    for md_file in track(md_files, description="Searching through files"):
        # Read the file content directly
        with open(collection_path / md_file, "r") as f:
            content = f.readlines()
            # Parse sections using the search parser directly
            sections = MdParser._parse_for_search(None, content)
        
        for section in sections:
            # Ask LLM if this section is relevant to the query
            llm_output = single_message_non_dialogue_interaction_with_llm(
                llm_server_url=cfg.llm_server_url,
                system_prompt=cfg.prompts.search.system_prompt,
                user_prompt_prefix=cfg.prompts.search.user_prompt_prefix,
                user_prompt_question=query,
                user_prompt_suffix=cfg.prompts.search.user_prompt_suffix,
                user_prompt_extra_content=f"{section['header']}\n\n{section['content']}",
            )
            
            is_relevant = to_boolean(llm_output)
            if is_relevant:
                results.append({
                    "file": md_file,
                    "header": section["header"],
                    "content": section["content"],
                })
    
    # Display results
    if results:
        console.print("\n[bold blue]Relevant sections found:[/bold blue]")
        console.rule(style="blue")
        
        for result in results:
            title = Text(f"📄 {result['file']} → {result['header']}", style="yellow bold")
            content = Text(result['content'])
            panel = Panel(
                content,
                title=title,
                border_style="blue",
                padding=(1, 2)
            )
            console.print(panel)
            console.print()
    else:
        console.print("\n[bold red]No relevant content found.[/bold red]")

def study(study_path: str, cfg: DictConfig) -> None:
    _print_mode_title(study.__name__)
    # Collect all the subjects in the study dir
    study_path = Path(study_path)
    subjects = [d.name for d in study_path.iterdir() if d.is_dir()]
    _print_list_with_numeric_options(title="study", files_or_dirs=subjects)

    # Choose the subject
    subject_i = prompt_until_satisfied(
        prompt_msg="Choose the subject by its number",
        input_prompt="> ",
        msg_if_satisfied="Looking for the topics",
        msg_if_not_satisfied="Wrong number. Try again",
        condition=lambda i_as_str: 1 <= int(i_as_str) <= len(subjects),
    )
    subject = subjects[int(subject_i) - 1]

    # Collect all the topics within the subject
    excluded_filenames = (
        "definitions.md",
    )
    subject_path = study_path / subject
    topic_md_files = get_markdown_filenames(p=subject_path, excluded_filenames=excluded_filenames)
    _print_list_with_numeric_options(title=subject, files_or_dirs=topic_md_files)

    # Choose the topic
    topic_i = prompt_until_satisfied(
        prompt_msg="Choose the topic by its number",
        input_prompt="> ",
        msg_if_satisfied="Generating a random question",
        msg_if_not_satisfied="Wrong number. Try again",
        condition=lambda i_as_str: 1 <= int(i_as_str) <= len(topic_md_files),
    )
    topic_md_file = topic_md_files[int(topic_i) - 1]

    # Parse the md file
    parser = MdParser(subject_path / topic_md_file, cfg.schemas.study)
    d = parser.parse()
    
    # Choose a subtopic randomly (some of them may be empty, skip them)
    n_subtopics = len(d["current_state"])
    subtopic = ""
    while not subtopic:
        i = random.randint(0, n_subtopics - 1)
        subtopic = d["current_state"][i]["Topic"]

    llm_output = single_message_non_dialogue_interaction_with_llm(
        llm_server_url=cfg.llm_server_url,
        system_prompt=cfg.prompts.study.system_prompt, 
        user_prompt_prefix=cfg.prompts.study.user_prompt_prefix,
        user_prompt_question=cfg.prompts.study.user_prompt_question_at_startup,
        user_prompt_suffix=cfg.prompts.study.user_prompt_suffix,
        user_prompt_extra_content=f"Предмет: {subject}" + "\n" + f"Раздел: {subtopic}" + "\n",
    )

    print_llm_output(llm_output)
    

def _run_interaction_based_on_single_md_file(
    md_path: str,
    prompts: DictConfig,
    llm_server_url: str,
    stop_word: str,
    ask_startup_question: bool,
) -> None:
    with open(md_path, "r") as f:
        md_file_content = f.read()
        if ask_startup_question:
            llm_output = single_message_non_dialogue_interaction_with_llm(
                llm_server_url=llm_server_url,
                system_prompt=prompts.system_prompt, 
                user_prompt_prefix=prompts.user_prompt_prefix,
                user_prompt_question=prompts.user_prompt_question_at_startup,
                user_prompt_suffix=prompts.user_prompt_suffix,
                user_prompt_extra_content=md_file_content,
            )
            print_llm_output(llm_output)

        recurrent_non_dialogue_interaction_with_llm(
            llm_server_url=llm_server_url,
            system_prompt=prompts.system_prompt, 
            user_prompt_prefix=prompts.user_prompt_prefix,
            user_prompt_suffix=prompts.user_prompt_suffix,
            user_prompt_extra_content=md_file_content,
            stop_word=stop_word,
        )


def _print_mode_title(mode_func_name: str) -> None:
    mode_name = mode_func_name.replace('_', ' ').upper() + " MODE"

    console.print()
    console.print(f"[bold blue on grey74]{mode_name:^{console.width}}[/bold blue on grey74]")
    console.print()


def _print_list_with_numeric_options(
    title: str,
    files_or_dirs: list[str],
    names: Optional[list[str]] = None,
    descriptions: Optional[list[str]] = None,
) -> None:
    console.rule(f"[bold blue]{title.upper()}[/bold blue]", style="blue")
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    for i, file_or_dir in enumerate(files_or_dirs):
        if names is not None:
            name = names[i]
        else:
            name = transform_filename_to_capitalized_name(file_or_dir)

        if descriptions is not None:
            descr = descriptions[i]

            table.add_row(
                f"[cyan]{i + 1}[/cyan]",
                Text(f"{name} - {descr}", style="green"),
                f"[dim]({file_or_dir})[/dim]"
            )
        else:
            table.add_row(
                f"[cyan]{i + 1}[/cyan]",
                Text(name, style="green"),
                f"[dim]({file_or_dir})[/dim]"
            )

    console.print(table)
    console.print()

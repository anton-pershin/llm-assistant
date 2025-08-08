from pathlib import Path
import random

from omegaconf import DictConfig
import feedparser
from tqdm import tqdm

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
    _run_interaction_based_on_single_md_file(
        md_path=cfg.routine_path,
        prompts=cfg.prompts.warmup,
        llm_server_url=cfg.llm_server_url,
        stop_word=cfg.stop_word,
        ask_startup_question=True,
    )


def relax(cfg: DictConfig) -> None:
    _run_interaction_based_on_single_md_file(
        md_path=cfg.relax_path,
        prompts=cfg.prompts.relax,
        llm_server_url=cfg.llm_server_url,
        stop_word=cfg.stop_word,
        ask_startup_question=False,
    )


def projects(project_path: str, cfg: DictConfig) -> None:
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
    md_buf = ""
    already_processed_titles = set()
    for rss_i, rss_url in enumerate(rss_feed_urls):
        feed = feedparser.parse(rss_url)
        if feed.status != 200:
            raise ValueError("Cannot get RSS feed, code: {feed.status}")

        for entry in tqdm(feed.entries, desc=f"RSS feed {rss_i + 1}/{len(rss_feed_urls)}"):
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
    # First, let user choose the collection
    collections = list(cfg.markdown_collections.keys())
    _print_list_with_numeric_options(
        title="collections", 
        files_or_dirs=[f"{k} - {cfg.markdown_collections[k].description}" for k in collections]
    )
    
    collection_i = prompt_until_satisfied(
        prompt_msg="Choose collection to search in by its number",
        input_prompt="> ",
        msg_if_satisfied="Selected collection",
        msg_if_not_satisfied="Wrong number. Try again",
        condition=lambda i_as_str: 1 <= int(i_as_str) <= len(collections),
    )
    selected_collection = collections[int(collection_i) - 1]
    collection_path = Path(cfg.markdown_collections[selected_collection].path)

    # Get query from user
    query = input("Enter your search query: ")
    
    # Get all markdown files recursively from selected collection
    excluded_filenames = ("definitions.md",)
    md_files = []
    for f in collection_path.rglob("*.md"):
        if f.name not in excluded_filenames:
            md_files.append(str(f.relative_to(collection_path)))
    
    results = []
    for md_file in md_files:
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
        print("\nRelevant sections found:")
        print("===="*8)
        for result in results:
            print(f"\nFile: {result['file']}")
            print(f"Section: {result['header']}")
            print(f"Content:\n{result['content']}")
            print("-"*32)
        print("\n" + "===="*8)
    else:
        print("\nNo relevant content found.")

def study(study_path: str, cfg: DictConfig) -> None:
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

    print(llm_output)
    

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


def _print_list_with_numeric_options(title: str, files_or_dirs: list[str]) -> None:
    print("===="*8)
    print(title.upper())
    print("===="*8 + "\n")

    print(f"{title.capitalize()} list:")
    for i, file_or_dir in enumerate(files_or_dirs):
        name = transform_filename_to_capitalized_name(file_or_dir)
        print(f"\t{i + 1}  " + name + f" ({file_or_dir})")
    print()

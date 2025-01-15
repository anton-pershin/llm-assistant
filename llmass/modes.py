from pathlib import Path
from omegaconf import DictConfig

from llmass.interaction import (
    single_message_non_dialogue_interaction_with_llm,
    recurrent_non_dialogue_interaction_with_llm,
)
from llmass.utils.common import (
    get_markdown_filenames,
    transform_filename_to_capitalized_name,
    prompt_until_satisfied,
)


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

    print("===="*8)
    print("Projects".upper())
    print("===="*8 + "\n")

    print("Project list:")
    for i, md_file in enumerate(project_md_files):
        student_name = transform_filename_to_capitalized_name(md_file)
        print(f"\t{i + 1}  " + student_name + f" ({md_file})")
    print()

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
            single_message_non_dialogue_interaction_with_llm(
                llm_server_url=llm_server_url,
                system_prompt=prompts.system_prompt, 
                user_prompt_prefix=prompts.user_prompt_prefix,
                user_prompt_question=prompts.user_prompt_question_at_startup,
                user_prompt_suffix=prompts.user_prompt_suffix,
                user_prompt_extra_content=md_file_content,
                stop_word=stop_word,
            )

        recurrent_non_dialogue_interaction_with_llm(
            llm_server_url=llm_server_url,
            system_prompt=prompts.system_prompt, 
            user_prompt_prefix=prompts.user_prompt_prefix,
            user_prompt_suffix=prompts.user_prompt_suffix,
            user_prompt_extra_content=md_file_content,
            stop_word=stop_word,
        )


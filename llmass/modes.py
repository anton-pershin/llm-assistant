from pathlib import Path
from omegaconf import DictConfig

from llmass.interaction import (
    single_message_non_dialogue_interaction_with_llm,
    recurrent_non_dialogue_interaction_with_llm,
)
from llmass.utils.common import (
    get_markdown_filenames,
    transform_filename_to_capitalized_name,
)

def warmup(cfg: DictConfig) -> None:
    # Read the routine md file
    with open(cfg.routine_path, "r") as f:
        md_file_content = f.read()
        single_message_non_dialogue_interaction_with_llm(
            llm_server_url=cfg.llm_server_url,
            system_prompt=cfg.prompts.warmup.system_prompt, 
            user_prompt_prefix=cfg.prompts.warmup.user_prompt_prefix,
            user_prompt_question=cfg.prompts.warmup.user_prompt_question_at_startup,
            user_prompt_suffix=cfg.prompts.warmup.user_prompt_suffix,
            user_prompt_extra_content=md_file_content,
            stop_word=cfg.stop_word,
        )

        recurrent_non_dialogue_interaction_with_llm(
            llm_server_url=cfg.llm_server_url,
            system_prompt=cfg.prompts.warmup.system_prompt, 
            user_prompt_prefix=cfg.prompts.warmup.user_prompt_prefix,
            user_prompt_suffix=cfg.prompts.warmup.user_prompt_suffix,
            user_prompt_extra_content=md_file_content,
            stop_word=cfg.stop_word,
        )


def projects(cfg: DictConfig) -> None:
    # Collect all the project files in the project dir
    project_md_files = []
    excluded_filenames = (
        "definitions.md",
    )
    project_path = Path(cfg.student_project_path)
    project_md_files = get_markdown_filenames(p=project_path, excluded_filenames=excluded_filenames)

    print("===="*8)
    print("Student projects".upper())
    print("===="*8 + "\n")

    print("Students:")
    for md_file in project_md_files:
        student_name = transform_filename_to_capitalized_name(md_file)
        print("\t" + student_name + f" ({md_file})")
    print()

    while True:
        md_file = prompt_until_satisfied(
            prompt_msg="Choose the file",
            input_prompt="> ",
            msg_if_satisfied="Running LLM conversation regarding this project",
            msg_if_not_satisfied="Wrong name. Try again",
            condition=lambda s: s in project_md_files,
        )

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

import requests
import json

from llmass.utils.common import print_llm_output
from llmass.utils.console import console, prompt_user


def compose_user_prompt(
    user_prompt_prefix: str,
    user_prompt_question: str,
    user_prompt_suffix: str,
    user_prompt_extra_content: str,
) -> str:
    return " ".join([user_prompt_prefix, user_prompt_question, user_prompt_suffix]) + "\n\n" + user_prompt_extra_content 


def single_message_non_dialogue_interaction_with_llm(
    llm_server_url: str,
    system_prompt: str, 
    user_prompt_prefix: str,
    user_prompt_question: str,
    user_prompt_suffix: str,
    user_prompt_extra_content: str,
) -> str:
    r = requests.post(
        llm_server_url,
        headers={
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": compose_user_prompt(
                        user_prompt_prefix,
                        user_prompt_question,
                        user_prompt_suffix,
                        user_prompt_extra_content
                    ),
                },
            ],
        }),
    )
    response_json = json.loads(r.text)
    assert len(response_json["choices"]) == 1, "Only single message in choices is supported"

    return response_json["choices"][0]["message"]["content"]


def recurrent_non_dialogue_interaction_with_llm(
    llm_server_url: str,
    system_prompt: str, 
    user_prompt_prefix: str,
    user_prompt_suffix: str,
    user_prompt_extra_content: str,
    stop_word: str = "stop",
) -> None:
    while True:
        q = prompt_user()
        if q == stop_word:
            break

        llm_output = single_message_non_dialogue_interaction_with_llm(
            llm_server_url=llm_server_url,
            system_prompt=system_prompt, 
            user_prompt_prefix=user_prompt_prefix,
            user_prompt_question=q,
            user_prompt_suffix=user_prompt_suffix,
            user_prompt_extra_content=user_prompt_extra_content,
        )
        print_llm_output(llm_output)


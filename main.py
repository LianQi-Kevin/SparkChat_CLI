from __future__ import print_function, unicode_literals

import json
import logging
import os
import time
from typing import List, Literal, Dict
from uuid import uuid4

from PyInquirer import prompt

from tools.SparkApi import SparkApi, get_spark_url
from tools.SparkTypes import SparkRequestParameterChat, SparkResponse

# from tools.logging_utils import log_set

# from rich.console import Console
# from rich.markdown import Markdown

# from rich import inspect

DEFAULT_CONFIG = {
    "temperature": 0.5,
    "max_tokens": 4096,
    "top_k": 4,
    "model_version": "3.0"
}

ON_MESSAGES = 2


def load_config(config_path: str = "config.json", ask: bool = False) -> Dict[str, str]:
    """Load the config file from config path."""

    def required_exists(config_, required_keys: List[str] = None):
        """Check if the required keys exist in the config file."""
        required_keys = ['api_key', 'api_secret', 'app_id'] if required_keys is None else required_keys
        return all(config_.get(key) for key in required_keys)

    config = DEFAULT_CONFIG.copy()

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config.update(json.loads("".join(f.readlines())))
    elif not os.path.exists(config_path) and not ask:
        raise FileNotFoundError(f"Config file not found at {config_path}.")

    if ask:
        api_questions = [
            {'type': 'input', 'name': 'app_id', 'message': 'The APPID for the Spark API.',
             'default': config.get('app_id', '')},
            {'type': 'input', 'name': 'api_key', 'message': 'The API key for authentication.',
             'default': config.get('api_key', '')},
            {'type': 'input', 'name': 'api_secret',
             'message': 'The API secret key used to generate the HMAC signature.',
             'default': config.get('api_secret', '')},
            {'type': 'list', 'name': 'model_version', 'message': 'The domain for the Spark API.',
             'choices': ['1.5', '2.0', '3.0', '3.5'],
             'default': config.get('model_version', DEFAULT_CONFIG["model_version"])},
            {'type': 'input', 'name': 'temperature', 'message': 'The temperature for the Spark model. (0.0 - 1.0)',
             'default': str(config.get('temperature', DEFAULT_CONFIG["temperature"]))},
            {'type': 'input', 'name': 'max_tokens',
             'message': 'The maximum number of tokens for the Spark model. (1 - 8192)',
             'default': str(config.get('max_tokens', DEFAULT_CONFIG["max_tokens"]))},
            {'type': 'input', 'name': 'top_k', 'message': 'The top k for the Spark model. (1 - 6)',
             'default': str(config.get('top_k', DEFAULT_CONFIG["top_k"]))}
        ]

        answers = prompt(api_questions)

        while not required_exists(answers):
            print("'api_key' and 'api_secret' and 'app_id' must set. Please type again.")
            answers = prompt(api_questions[0: 3])

        with open(config_path, "w") as f:
            f.write(json.dumps(answers, indent=4))

        config.update(answers)
    assert required_exists(config), ValueError(
        "The config file does not contain the required fields: 'api_key', 'api_secret', 'app_id'.")
    return config


class SparkChat(SparkApi):
    def __init__(self, app_id: str, api_key: str, api_secret: str, userid: str = uuid4().hex,
                 system_msg: str = "Your a helpful assistant.",
                 model_version: Literal['1.5', '2.0', '3.0', '3.5'] = "1.5"):
        # API
        super().__init__(app_id, api_key, api_secret, userid, system_msg, model_version)

        # self.console = Console()

    def on_message(self, ws, message):
        # print(f"Received a message. {message}")
        global ON_MESSAGES
        logging.debug(message)
        data = SparkResponse(**json.loads(message)).model_dump()
        if data["header"]["code"] != 0:
            print(f'请求错误: {data["header"]["code"]}, {data}')
            self.ws.close()
        else:
            content = data["payload"]["choices"]["text"][0]["content"]
            print(content, end="")
            # self.console.print(Markdown(content))
            self.result += content
            ON_MESSAGES = data["payload"]["choices"]["status"]
            if data["payload"]["choices"]["status"] == 2:
                print('')
                self.conversations.append({"role": "assistant", "content": self.result})
                self.ws.close()

    def ws_run(self, params: SparkRequestParameterChat = None):
        global ON_MESSAGES
        # print("Running the websocket.")
        while True:
            if self.ws is None:
                self.ws_start(enableTrace=False)
            while ON_MESSAGES != 2:
                time.sleep(1)
            user_message = input("You: ")
            if user_message.lower() == "exit":
                break
            self.ws.send(self.gen_params(user_message, params))
            # self.console.print(Markdown(f"星火: "))
            print("星火: ", end=" ")

            ON_MESSAGES = 0


def main():
    # log_set(logging.DEBUG)
    config = load_config(ask=True)

    domain, _ = get_spark_url(config["model_version"])
    config["domain"] = domain

    print(config)

    spark_chat = SparkChat(
        app_id=config["app_id"],
        api_key=config["api_key"],
        api_secret=config["api_secret"],
        model_version=config["model_version"]
    )
    spark_chat.ws_run(params=SparkRequestParameterChat(**config))


if __name__ == '__main__':
    main()

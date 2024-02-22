import json
import logging
import os
from typing import List

from PyInquirer import prompt

from tools.SparkApi import SparkApi
from tools.SparkTypes import SparkRequestParameterChat
from tools.logging_utils import log_set

DEFAULT_CONFIG = {"temperature": 0.5, "max_tokens": 4096, "top_k": 4, "model_version": "3.0"}


def load_config(config_path: str = "config.json", ask: bool = False) -> dict:
    """Load the config file from config path."""

    def required_exists(config_, required_keys: List[str] = None):
        """Check if the required keys exist in the config file."""
        required_keys = ['api_key', 'api_secret', 'app_id'] if required_keys is None else required_keys
        return all(config_.get(key) for key in required_keys)

    _config = DEFAULT_CONFIG.copy()

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            _config.update(json.loads("".join(f.readlines())))
    elif not os.path.exists(config_path) and not ask:
        raise FileNotFoundError(f"Config file not found at {config_path}.")

    if ask:
        api_questions = [
            {
                'type': 'input',
                'name': 'app_id',
                'message': 'The APPID for the Spark API.',
                'default': _config.get('app_id', '')
            },
            {
                'type': 'input',
                'name': 'api_key',
                'message': 'The API key for authentication.',
                'default': _config.get('api_key', '')
            },
            {
                'type': 'input',
                'name': 'api_secret',
                'message': 'The API secret key used to generate the HMAC signature.',
                'default': _config.get('api_secret', '')
            },
            {
                'type': 'list',
                'name': 'model_version',
                'message': 'The domain for the Spark API.',
                'choices': ['1.5', '2.0', '3.0', '3.5'],
                'default': _config.get('model_version', DEFAULT_CONFIG["model_version"])
            },
            {
                'type': 'input',
                'name': 'temperature',
                'message': 'The temperature for the Spark model. (0.0 - 1.0)',
                'default': str(_config.get('temperature', DEFAULT_CONFIG["temperature"]))},
            {
                'type': 'input',
                'name': 'max_tokens',
                'message': 'The maximum number of tokens for the Spark model. (1 - 8192)',
                'default': str(_config.get('max_tokens', DEFAULT_CONFIG["max_tokens"]))},
            {
                'type': 'input',
                'name': 'top_k',
                'message': 'The top k for the Spark model. (1 - 6)',
                'default': str(_config.get('top_k', DEFAULT_CONFIG["top_k"]))
            }
        ]

        answers = prompt(api_questions)

        while not required_exists(answers):
            print("'api_key' and 'api_secret' and 'app_id' must set. Please type again.")
            answers = prompt(api_questions[0: 3])

        with open(config_path, "w") as f:
            f.write(json.dumps(answers, indent=4))

        _config.update(answers)
    assert required_exists(_config), ValueError(
        "The config file does not contain the required fields: 'api_key', 'api_secret', 'app_id'.")
    print("\n")
    return _config


if __name__ == '__main__':
    log_set(logging.ERROR)
    config = load_config(ask=os.path.exists("config.json") is False)
    spark = SparkApi(
        APPID=config["app_id"],
        APIKey=config["api_key"],
        APISecret=config["api_secret"],
        model_version=config["model_version"],
        params=SparkRequestParameterChat(**config)
    )

    while not spark.connect_error:
        if spark.status_code != 2:
            continue
        spark.ws_start()

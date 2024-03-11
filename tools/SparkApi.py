import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime
from email.utils import formatdate
from typing import Tuple, Literal, Dict, List
from urllib.parse import urlencode, urlparse
from uuid import uuid4

import websocket

from tools.SparkTypes import SparkRequest, SparkRequestParameterChat, SparkResponse
from tools.logging_utils import log_set


EXIT_COMMANDS = ["exit", "exit()", "break", "quit", "stop"]


def get_length(conversations: List[Dict[str, str]]):
    length = 0
    for content in conversations:
        length += len(content["content"])
    return length


def check_len(conversations: List[Dict[str, str]]):
    while get_length(conversations) > 8000:
        del conversations[0]
    return conversations


def get_spark_url(version: Literal['1.5', '2.0', '3.0', '3.5'] = '1.5') -> Tuple[str, str]:
    """
    获取讯飞语音交互API的URL
    :returns: (domain, spark_url)
    """
    if version == '1.5':
        return "general", "wss://spark-api.xf-yun.com/v1.1/chat"
    elif version == '2.0':
        return "generalv2", "wss://spark-api.xf-yun.com/v2.1/chat"
    elif version == '3.0':
        return "generalv3", "wss://spark-api.xf-yun.com/v3.1/chat"
    elif version == '3.5':
        return "generalv3.5", "wss://spark-api.xf-yun.com/v3.5/chat"
    else:
        raise ValueError(f"不支持的API版本号: {version}")


class SparkApi(object):
    def __init__(self, APPID: str, APIKey: str, APISecret: str, userid: str = uuid4().hex,
                 params: SparkRequestParameterChat = None,
                 system_msg: str = "Your a helpful assistant.",
                 model_version: Literal['1.5', '2.0', '3.0', '3.5'] = "1.5",
                 save_history: bool = False, history_path: str = "history"):
        # API
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.domain, self.sparkUrl = get_spark_url(version=model_version)
        self.params = params if params is not None else SparkRequestParameterChat()
        self.params.domain = self.domain

        # Chat
        self.ws = None
        self.uid = userid
        self.chat_id = f"{datetime.now().strftime('%y%m%d%H%M%S')}_{str(uuid4())[:8]}"
        self.result = ""
        self.conversations = [{"role": "system", "content": system_msg}] if model_version == "3.5" else []
        self.connect_error = False
        self.status_code = 2

        # history cache
        self.save_history = save_history
        self.history_path = history_path
        self.chat_cache_path = os.path.join(self.history_path, f"chat_{self.chat_id}.txt")
        self._init_history()

    def _init_history(self):
        if self.save_history:
            os.makedirs(os.path.dirname(self.chat_cache_path), exist_ok=True)

            with open(self.chat_cache_path, "w") as f:
                f.write(f"-------      Info       ------\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Chat ID: {self.chat_id}\n\n")
                f.write(f"-------  Conversations  ------\n")

    def create_url(self, spark_url: str = "wss://spark-api.xf-yun.com/v1.1/chat") -> str:
        """
        生成带有鉴权参数的URL
        """
        # 生成RFC1123格式的时间戳
        date = formatdate(usegmt=True)

        # 构建签名原文
        parsed_url = urlparse(spark_url)
        signature_origin = f"host: {parsed_url.netloc}\ndate: {date}\nGET {parsed_url.path} HTTP/1.1"

        # 使用HMAC-SHA256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        # 构建授权头
        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 构造请求鉴权参数
        auth_params = {"authorization": authorization, "date": date, "host": parsed_url.netloc}

        # 拼接鉴权参数，生成url
        return f"{spark_url}?{urlencode(auth_params)}"

    def gen_params(self, user_message: str) -> str:
        self.conversations.append({"role": "user", "content": user_message})
        request_params = {
            "header": {"app_id": self.APPID, "uid": self.uid},
            "parameter": {"chat": {"domain": self.domain, "chat_id": self.chat_id}},
            "payload": {"message": {"text": check_len(self.conversations)}}
        }

        request_params["parameter"]["chat"].update(self.params.model_dump())

        # verify params && to json
        return SparkRequest(**request_params).model_dump_json()

    def ws_start(self, enableTrace: bool = False):
        websocket.enableTrace(enableTrace)
        self.ws = websocket.WebSocketApp(url=self.create_url(self.sparkUrl), on_open=self.on_open,
                                         on_message=self.on_message, on_close=self.on_close,
                                         on_error=self.on_error)
        self.ws.run_forever()

    def ws_run(self):
        user_message = input("You: ")

        if user_message in EXIT_COMMANDS:
            self.ws.close()
            self.connect_error = True
            time.sleep(2)
            return

        if self.save_history and user_message not in EXIT_COMMANDS:
            with open(self.chat_cache_path, "a") as f:
                f.write(f"You: {user_message}\n")

        data = self.gen_params(user_message)
        logging.debug(f"Request data: {data}")

        self.ws.send(data)

        print("星火: ", end=" ")

    def on_open(self, ws):
        threading.Thread(target=self.ws_run).start()

    def on_message(self, ws, message):
        logging.debug(message)
        data = SparkResponse(**json.loads(message))

        if data.header.code != 0:
            logging.error(f'请求错误: {data.header.code}, {data}')
            self.on_error(None, data.header.message)
        else:
            content = data.payload.choices.text[0].content
            print(content, end="")
            self.result += content
            self.status_code = data.payload.choices.status
            if self.status_code == 2:
                self.conversations.append({"role": "assistant", "content": self.result})
                self.ws.close()
                if self.save_history:
                    with open(self.chat_cache_path, "a") as f:
                        f.write(f"Spark: {self.result}\n")

    def on_close(self, ws, one, two):
        logging.debug("### Connection closed ###")
        # self.chat_id = f"{datetime.now().strftime('%y%m%d%H%M%S')}_{str(uuid4())[:8]}"
        self.result = ""
        print(" ")

    def on_error(self, ws, error):
        logging.error(f"### Connection ERROR")
        logging.debug(f"### error message: {error}")
        self.connect_error = True


if __name__ == '__main__':
    log_set(logging.DEBUG)

    config = {
        "app_id": "",
        "api_key": "",
        "api_secret": "",
    }

    spark = SparkApi(
        APPID=config["app_id"],
        APIKey=config["api_key"],
        APISecret=config["api_secret"],
        model_version="3.5")

    while not spark.connect_error:
        if spark.status_code != 2:
            continue
        spark.ws_start(enableTrace=True)
        time.sleep(1)

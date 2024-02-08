import base64
import hashlib
import hmac
import json
import logging
import threading
import time
from datetime import datetime
from email.utils import formatdate
from typing import Tuple
from urllib.parse import urlencode, urlparse
from uuid import uuid4

import websocket
from dotenv import dotenv_values
from pydantic import ValidationError

from tools.SparkTypes import SparkRequest, SparkRequestParameterChat, SparkResponse
from tools.logging_utils import log_set


def get_spark_url(version: str = '1.5') -> Tuple[str, str]:
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
    # todo: 使用时继承该类，并覆盖on_message和ws_run方法
    def __init__(self, APPID: str, APIKey: str, APISecret: str, userid: str = None,
                 system_msg: str = "Your a helpful assistant.", model_version: str = "1.5"):
        # API
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.domain, self.sparkUrl = get_spark_url(version=model_version)

        # Chat
        self.ws = None
        self.uid = userid if userid is not None else uuid4().hex
        self.chat_id = f"{datetime.now().strftime('%y%m%d%H%M%S')}_{str(uuid4())[:8]}"
        self.result = ""
        self.conversations = [{"role": "system", "content": system_msg}]
        # self.conversations = []

        self.ws_start()

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

    def gen_params(self, user_message: str, params: SparkRequestParameterChat = None) -> str:
        self.conversations.append({"role": "user", "content": user_message})
        request_params = {
            "header": {"app_id": self.APPID, "uid": self.uid},
            "parameter": {"chat": {"domain": self.domain, "chat_id": self.chat_id}},
            "payload": {"message": {"text": self.conversations}}}

        if params:
            request_params["parameter"]["chat"].update(params.model_dump())

        # verify params && to json
        return SparkRequest(**request_params).model_dump_json()

    def ws_start(self, enableTrace: bool = False):
        websocket.enableTrace(enableTrace)
        self.ws = websocket.WebSocketApp(
            url=self.create_url(self.sparkUrl),
            on_open=self.on_open,
            on_message=self.on_message,
            on_close=self.on_close,
            on_error=self.on_error,
        )
        self.ws.run_forever()

    def ws_run(self, params: SparkRequestParameterChat = None):
        time.sleep(1)
        user_message = input("You: ")

        if user_message == "exit":
            self.ws.close()
            exit()

        try:
            self.ws.send(self.gen_params(user_message, params))
        except ValidationError as e:
            print(e)

        print("星火: ", end=" ")

    def on_open(self, ws):
        threading.Thread(target=self.ws_run).start()

    def on_message(self, ws, message):
        logging.debug(message)
        data = SparkResponse(**json.loads(message)).model_dump()
        if data["header"]["code"] != 0:
            print(f'请求错误: {data["header"]["code"]}, {data}')
            self.ws.close()
        else:
            content = data["payload"]["choices"]["text"][0]["content"]
            print(content, end="")
            self.result += content
            if data["payload"]["choices"]["status"] == 2:
                print('\n')
                self.conversations.append({"role": "assistant", "content": self.result})
                self.ws.close()

    def on_close(self, ws, one, two):
        logging.debug("### Connection closed ###")
        self.chat_id = f"{datetime.now().strftime('%y%m%d%H%M%S')}_{str(uuid4())[:8]}"
        self.result = ""
        self.ws_start()

    @staticmethod
    def on_error(ws, error):
        logging.error(f"### error: {error}")


if __name__ == '__main__':
    log_set(logging.INFO)

    config = {
        **dotenv_values("../.env"),
        **dotenv_values("../.env.local"),
    }

    spark = SparkApi(
        APPID=config["Spark_APPID"],
        APIKey=config["Spark_APIKey"],
        APISecret=config["Spark_APISecret"],
        model_version="1.5")
    spark.ws_run()

import base64
import hashlib
import hmac
from email.utils import formatdate
from typing import Tuple
from urllib.parse import urlencode, urlparse


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
    # 初始化
    def __init__(self, APPID: str, APIKey: str, APISecret: str):
        # API
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret

    def create_url(self, Spark_url: str = "wss://spark-api.xf-yun.com/v1.1/chat") -> str:
        """
        生成带有鉴权参数的URL
        """
        # 生成RFC1123格式的时间戳
        date = formatdate(usegmt=True)

        # 构建签名原文
        parsed_url = urlparse(Spark_url)
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
        return f"{Spark_url}?{urlencode(auth_params)}"

    def wsSend(self, conversations):
        # 生成url
        url = self.create_url()
        return url

from datetime import datetime
from typing import Literal, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SparkRequestHeader(BaseModel):
    app_id: str
    uid: str = Field(max_length=32, default=uuid4().hex)


class SparkRequestParameterChat(BaseModel):
    domain: Literal['general', 'generalv2', 'generalv3', 'generalv3.5'] = Field(default='general')
    temperature: float = Field(default=0.5, ge=0, le=1)
    max_tokens: int = Field(default=4096, ge=1, le=8192)
    top_k: int = Field(default=4, ge=1, le=6)
    chat_id: str = Field(default_factory=lambda: f"{datetime.now().strftime('%y%m%d%H%M%S')}_{str(uuid4())[:8]}")


class SparkRequestPayloadMessageText(BaseModel):
    role: Literal['user', 'system', 'assistant']
    content: str


class SparkRequestPayloadMessage(BaseModel):
    text: List[SparkRequestPayloadMessageText]


class SparkRequestParameter(BaseModel):
    chat: SparkRequestParameterChat = Field(default_factory=SparkRequestParameterChat)


class SparkRequestPayload(BaseModel):
    message: SparkRequestPayloadMessage
    # todo: add Function Call
    # functions: None = Field(default=None)


class SparkRequest(BaseModel):
    header: SparkRequestHeader
    parameter: SparkRequestParameter = Field(default_factory=SparkRequestParameter)
    payload: SparkRequestPayload


class SparkResponseHeader(BaseModel):
    code: int
    message: str
    sid: str
    status: int


class SparkResponsePayloadChoicesText(BaseModel):
    content: str
    role: str = Field(default="assistant")
    index: int


class SparkResponsePayloadChoices(BaseModel):
    status: int
    seq: int
    text: List[SparkRequestPayloadMessageText]


class SparkResponsePayloadUsageText(BaseModel):
    question_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class SparkResponsePayloadUsage(BaseModel):
    text: SparkResponsePayloadUsageText


class SparkResponsePayload(BaseModel):
    choices: SparkResponsePayloadChoices
    usage: Optional[SparkResponsePayloadUsage] = Field(default=None)


class SparkResponse(BaseModel):
    header: SparkResponseHeader
    payload: SparkResponsePayload = None


if __name__ == '__main__':
    request_example = {
        "header": {"app_id": "5d1ce7a1"},
        "payload": {
            "message": {"text": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hello"},
                                 {"role": "user", "content": "What can you do?"}]}}}
    print(SparkRequest(**request_example).model_dump())

    response_example = {
        "header": {"code": 0, "message": "Success", "sid": "cht000cb087@dx18793cd421fb894542", "status": 2},
        "payload": {
            "choices": {"status": 2, "seq": 0,
                        "text": [{"content": "我可以帮助你的吗？", "role": "assistant", "index": 0}]},
            "usage": {"text": {"question_tokens": 4, "prompt_tokens": 5, "completion_tokens": 9, "total_tokens": 14}}
        }}
    print(SparkResponse(**response_example).model_dump())

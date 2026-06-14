from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    conversation_id: str | None = Field(default=None, alias="conversationId")
    source_type: str = Field(default="workspace", alias="sourceType", max_length=40)
    source_id: str | None = Field(default=None, alias="sourceId")
    title: str | None = Field(default=None, max_length=255)


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str
    model: str
    mock: bool = False
    conversation_id: str | None = Field(default=None, alias="conversationId")
    message_id: str | None = Field(default=None, alias="messageId")
    usage: dict = Field(default_factory=dict)

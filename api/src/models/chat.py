from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class TextPart(BaseModel):
    type: Literal["text"]
    text: str = Field(max_length=100_000)


class StepStartPart(BaseModel):
    type: Literal["step-start"]


class Message(BaseModel):
    id: str = Field(min_length=1, max_length=256)
    role: Literal["user", "assistant"]
    parts: list[Annotated[TextPart | StepStartPart, Field(discriminator="type")]] = Field(
        min_length=1, max_length=100
    )

    @property
    def text(self) -> str:
        return "".join(part.text for part in self.parts if isinstance(part, TextPart))


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def limit_conversation(self):
        if sum(len(message.text) for message in self.messages) > 100_000:
            raise ValueError("Please send a shorter conversation.")
        return self

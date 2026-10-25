from uuid import uuid4
from typing import Literal, Annotated
from pydantic import Field, BaseModel, model_validator


class TextPart(BaseModel):
    """Represent a bounded text segment in a chat message."""

    type: Literal["text"]
    text: str = Field(max_length=100_000)


class StepStartPart(BaseModel):
    """Represent an AI SDK step-start marker."""

    type: Literal["step-start"]


class Message(BaseModel):
    """Validate a user or assistant message and its content parts."""

    id: str = Field(min_length=1, max_length=256)
    role: Literal["user", "assistant"]
    parts: list[Annotated[TextPart | StepStartPart, Field(discriminator="type")]] = Field(min_length=1, max_length=100)

    @property
    def text(self) -> str:
        """Concatenate text parts while excluding protocol markers."""
        return "".join(part.text for part in self.parts if isinstance(part, TextPart))


class ChatRequest(BaseModel):
    """Validate the messages supplied to a chat request."""

    # Keep SDK conversation identity while supporting clients without an ID.
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=256)
    messages: list[Message] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def limit_conversation(self):
        """Reject conversations exceeding the total character limit."""
        if sum(len(message.text) for message in self.messages) > 100_000:
            raise ValueError("Please send a shorter conversation.")
        return self

import fsspec
import logging
from uuid import uuid4
from typing import Literal
from pathlib import Path
from datetime import UTC, datetime
from pydantic import Field, BaseModel, JsonValue

logger = logging.getLogger(__name__)
TraceEventType = Literal["user message", "assistant message", "thinking", "tool call", "tool result", "model output", "error"]


class TraceEvent(BaseModel):
    """Represent one timestamped event without hidden model reasoning."""

    # Describe the event and its JSON-serializable payload.
    data: JsonValue
    event: TraceEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatTrace(BaseModel):
    """Persist one chat request's public messages and execution trace."""

    # Identify the request and its completion state.
    id: str = Field(default_factory=lambda: str(uuid4()))
    model: str
    status: Literal["interrupted", "completed", "error"] = "interrupted"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Retain ordered events for JSON exports.
    events: list[TraceEvent] = Field(default_factory=list)

    def record(self, event: TraceEventType, data: JsonValue) -> None:
        """Append an event, combining adjacent streamed model text deltas."""
        if event == "model output" and self.events and self.events[-1].event == event:
            previous = self.events[-1]
            if isinstance(previous.data, str) and isinstance(data, str):
                previous.data += data
                return
        self.events.append(TraceEvent(event=event, data=data))

    def save(self, directory: Path) -> None:
        """Write a JSON file through fsspec without exposing storage errors to chat clients."""

        # Keep persistence failures out of an otherwise valid streamed response.
        try:
            with fsspec.open(str(directory / f"{self.id}.json"), "wt", encoding="utf-8", auto_mkdir=True) as file:
                file.write(self.model_dump_json(indent=2))
        except OSError:
            logger.exception("Could not save chat trace %s", self.id)

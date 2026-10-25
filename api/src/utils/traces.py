import hashlib
import logging
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
    """Persist a conversation and its latest execution trace."""

    # Identify the conversation and its latest completion state.
    model: str
    status: Literal["interrupted", "completed", "error"] = "interrupted"
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    conversation_id: str

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
        """Replace the conversation's JSON snapshot without disrupting chat."""

        # Keep persistence failures out of an otherwise valid streamed response.
        try:
            directory.mkdir(parents=True, exist_ok=True)

            # Hash client-supplied IDs so they cannot become filesystem paths.
            filename = hashlib.sha256(self.conversation_id.encode("utf-8")).hexdigest()
            (directory / f"{filename}.json").write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")
        except OSError:
            logger.exception("Could not save chat trace %s", self.conversation_id)

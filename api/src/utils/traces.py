import fcntl
import hashlib
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
        """Append a turn to its conversation's JSONL log without disrupting chat."""

        # Keep persistence failures out of an otherwise valid streamed response.
        try:
            directory.mkdir(parents=True, exist_ok=True)

            # Hash client-supplied IDs so they cannot become filesystem paths.
            filename = hashlib.sha256(self.conversation_id.encode("utf-8")).hexdigest()
            with (directory / f"{filename}.jsonl").open("a", encoding="utf-8") as output:
                # Serialize appends across requests and worker processes until the file closes.
                fcntl.flock(output, fcntl.LOCK_EX)
                output.write(self.model_dump_json() + "\n")
        except OSError:
            logger.exception("Could not save chat trace %s", self.id)

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Button:
    """A channel button whose token is an opaque identifier."""

    label: str
    token: str


@runtime_checkable
class MessagingChannel(Protocol):
    """Contract implemented by outbound messaging channels."""

    name: str

    def send(self, external_id: str, text: str) -> str: ...

    def send_with_buttons(
        self,
        external_id: str,
        text: str,
        buttons: list[Button],
    ) -> str: ...

    def max_message_length(self) -> int: ...

    def format(self, text: str) -> str: ...

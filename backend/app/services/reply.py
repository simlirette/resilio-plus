"""Separate what the coach worked out from what the athlete reads.

On the first live conversation the model produced its working notes and its
reply in one block, and the whole thing was forwarded to Telegram:

    Profil reçu depuis l'onboarding :
    ...
    Ces données sont déjà enregistrées. Rien à collecter ici.
    ---
    Message à l'athlète :
    Ton profil de base est enregistré...

A later message opened with ``Athlete #1a2d73d5 — Profil initial``. The athlete
saw the machinery, a database row identifier, and a label announcing where the
real answer started.

Two layers, deliberately:

  - **The contract** asks the model to wrap the athlete-facing part in
    ``<message>`` tags. That covers the ordinary case cheaply.
  - **The scrubber** runs regardless. A model that ignores the contract must
    still not be able to leak an identifier, and a guard that only works when
    the model cooperates is not a guard.

Neither ever blanks a reply. An imperfect message reaches the athlete;
returning nothing would end the conversation over a formatting problem.
"""
from __future__ import annotations

import re

#: Appended to the user turn rather than the system prompt, so `agents/prompts.py`
#: -- frozen since V1 -- stays untouched.
OUTPUT_CONTRACT = (
    "\n\nFormat de réponse : mets le texte destiné à l'athlète entre "
    "<message> et </message>. Tout raisonnement interne va en dehors de ces "
    "balises et ne sera pas transmis. N'écris jamais d'identifiant interne."
)

_MESSAGE_TAG = re.compile(r"<message>(.*?)</message>", re.DOTALL | re.IGNORECASE)

#: The prose separator the model actually used when left to its own devices.
_LEGACY_LABEL = re.compile(
    r"^.*?message\s+(?:à|a)\s+l['’]?ath?l[eè]te\s*:?\s*$"
    r"|^.*?message\s+to\s+athlete\s*:?\s*$",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)

_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
#: `Athlete #1a2d73d5` — the short form the model invented.
_ATHLETE_LABEL = re.compile(
    r"\bathlete\s*#\s*[0-9a-f-]{6,}\s*(?:[-—–]\s*)?", re.IGNORECASE
)
_THREAD_LABEL = re.compile(r"\bthread\s+\S+", re.IGNORECASE)


def _strip_identifiers(text: str) -> str:
    text = _ATHLETE_LABEL.sub("", text)
    text = _THREAD_LABEL.sub("", text)
    text = _UUID.sub("", text)
    return text


_RULE_LINE = {"---", "—", "–", "***"}


def _tidy(text: str) -> str:
    """Collapse the blank lines and stray rules left behind by a removal."""
    collapsed: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip() in _RULE_LINE:
            continue
        if not line.strip() and (not collapsed or not collapsed[-1].strip()):
            continue
        collapsed.append(line)
    return "\n".join(collapsed).strip()


def athlete_facing(raw: str) -> str:
    """Return only the part of a model reply that should be sent.

    Falls back to the whole reply whenever the contract is absent or empty --
    most replies carry no scaffolding at all, and an unmarked one is far more
    likely to be a clean answer than a mistake.
    """
    if not raw:
        return ""

    tagged = _MESSAGE_TAG.search(raw)
    body = tagged.group(1) if tagged and tagged.group(1).strip() else raw

    if not tagged:
        label = _LEGACY_LABEL.search(body)
        if label:
            body = body[label.end() :]

    return _tidy(_strip_identifiers(body))

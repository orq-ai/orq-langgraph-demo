"""Shared orq-ai-sdk client factory.

Every module that talks to orq.ai via the SDK should go through this
factory so the `ORQ_API_BASE` override is honored consistently across
routes (raw HTTP in scripts, LLM router, OTEL exporter, SDK calls).

The SDK prepends `/v2/...` to every path internally (see
`orq_ai_sdk.agents.invoke_async` etc.), so the SDK `server_url` must be
the host without the `/v2` suffix — whereas raw-HTTP callers want
`settings.ORQ_API_BASE` including `/v2`. `_derive_server_url()` bridges
the two conventions.

A single `Orq` instance carries both a `httpx.Client` and a
`httpx.AsyncClient` (see `orq_ai_sdk.sdk.Orq.__init__`), so one
process-wide singleton serves both sync and async call sites without
mixing transports.
"""

from __future__ import annotations

import os
from typing import Optional

from orq_ai_sdk import Orq

from core.settings import settings

_client: Optional[Orq] = None


def _derive_server_url() -> str:
    return settings.ORQ_API_BASE.rstrip("/").removesuffix("/v2")


def get_orq_client() -> Orq:
    """Return the process-wide Orq client, creating it on first call.

    Raises ``RuntimeError`` if ``ORQ_API_KEY`` is not set, since no call
    can succeed without it.
    """
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        raise RuntimeError("ORQ_API_KEY is not set")

    _client = Orq(api_key=api_key, server_url=_derive_server_url())
    return _client

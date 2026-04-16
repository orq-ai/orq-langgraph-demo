"""orq_ai_sdk callback-handler tracing backend.

Registers a LangChain ``BaseCallbackHandler`` via the configure-hook system.
Once ``setup_callback_tracing()`` has been called, every Runnable invocation —
and therefore every LangGraph node, tool call, and LLM call — automatically
emits OTLP spans to orq.ai without any OTEL boilerplate. Selected when
``ORQ_TRACING_BACKEND="callback"`` (the default).

If you prefer the explicit per-invocation pattern, instantiate
``OrqLangchainCallback`` yourself and thread it through
``.with_config({"callbacks": [handler]})``. Both are supported public APIs
of ``orq_ai_sdk.langchain``.

See ``LANGGRAPH-INTEGRATION.md`` for how this compares to the OTEL backend.
"""

import os

from orq_ai_sdk.langchain import setup as orq_langchain_setup

# Module-local idempotency flag. The earlier implementation reached into
# ``orq_ai_sdk.langchain._global._handler_var`` — the SDK's own source of
# truth — which is stronger (catches callers that bypass us and call
# ``orq_langchain_setup`` directly) but pins us to a private import that
# can move between SDK releases. The trade-off: if another module calls
# ``orq_langchain_setup`` before us, the handler will be installed twice
# by different entrypoints. In this repo ``setup_callback_tracing`` is
# the single entrypoint (called from ``assistant.graph`` and the eval
# scripts), so process-local tracking is sufficient.
_installed = False


def setup_callback_tracing() -> None:
    """Activate the orq.ai LangChain callback handler. Idempotent.

    The handler attaches to LangChain's configure-hook ContextVar, which is
    inheritable, so child Runnables (including every LangGraph node) pick it
    up automatically. Flush is handled by the SDK's ``OrqTracesClient`` —
    its ``__init__`` registers an ``atexit`` drain, so short-lived scripts
    don't lose final spans even though there's no explicit teardown call here.
    """
    global _installed
    if _installed:
        return

    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ORQ_API_KEY is required for the callback tracing backend. "
            "Set it in .env or switch ORQ_TRACING_BACKEND to 'none'."
        )

    orq_langchain_setup(api_key=api_key)
    _installed = True

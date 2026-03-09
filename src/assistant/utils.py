"""Utility & helper functions."""

import csv
from pathlib import Path
from typing import Dict, List, Union

from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from assistant.models import SearchResult

import os

def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def convert_search_result_to_document(search_result: SearchResult, tool_name: str) -> Document:
    """Convert a SearchResult object to a Document object.

    Args:
        search_result (SearchResult): The search result to convert.
        tool_name (str): The name of the tool that generated this result.

    Returns:
        Document: A Document object with the search result content and metadata.
    """
    return Document(
        page_content=search_result.content,
        metadata={
            "filename": search_result.filename,
            "page": search_result.page,
            "chunk_index": search_result.chunk_index,
            "relevance_score": search_result.relevance_score,
            "tool_used": tool_name,
        },
    )


def load_starters_from_csv(csv_path: Union[Path, str]) -> List[Dict[str, str]]:
    """Load starter messages from a CSV file.

    Args:
        csv_path (Union[Path, str]): Path to the CSV file containing starter data.
                                    Expected columns: 'label', 'message'

    Returns:
        List[Dict[str, str]]: List of dictionaries with 'label' and 'message' keys.

    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
        ValueError: If the CSV file is missing required columns.
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Starters CSV file not found: {csv_path}")

    starters = []

    try:
        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            # Validate required columns
            required_columns = {"label", "message"}
            if not required_columns.issubset(reader.fieldnames or []):
                raise ValueError(f"CSV file must contain columns: {required_columns}")

            for row in reader:
                label = row["label"].strip()
                message = row["message"].strip()

                if label and message:  # Skip empty rows
                    starters.append({"label": label, "message": message})

    except Exception as e:
        raise ValueError(f"Error reading starters CSV file: {e}") from e

    return starters


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'provider/model'.
    """
    provider, model = fully_specified_name.split("/", maxsplit=1)
    # return init_chat_model(model, model_provider=provider, api_key=os.getenv("ORQ_API_KEY"),
    # base_url="https://api.orq.ai/v2/router")
    return init_chat_model(model, model_provider=provider)

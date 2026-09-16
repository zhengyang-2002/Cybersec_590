"""Core scoring logic: validate the input, call the LLM once, return structured JSON.

All configuration comes from environment variables (see .env.example):
    LLM_API_KEY   - API key for an OpenAI-compatible endpoint
    LLM_BASE_URL  - defaults to https://api.deepseek.com
    LLM_MODEL     - defaults to deepseek-flash
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MIN_WORDS = 30
MAX_WORDS = 500
TEMPERATURE = 0.2  # ignored by the API in thinking mode

DIMENSIONS: list[tuple[str, str]] = [
    ("problem_motivation", "Problem & Motivation"),
    ("method_clarity", "Method Clarity"),
    ("results_evidence", "Results & Evidence"),
    ("contribution_novelty", "Contribution & Novelty"),
    ("structure_completeness", "Structure & Completeness"),
    ("language_readability", "Language & Readability"),
]

_DIMENSION_GUIDE = "\n".join(
    f'- "{key}": {label}' for key, label in DIMENSIONS
)

SYSTEM_PROMPT = f"""You are a strict but fair reviewer for academic paper abstracts.

You will receive either a block of text or an image. Follow these steps:

1. If you receive an image, transcribe all the text in it verbatim into "extracted_text".
   If you receive plain text, copy nothing and leave "extracted_text" as an empty string.
2. Decide whether the content is the ABSTRACT of a research paper. An abstract is a
   self-contained summary of a study: it normally states a problem, an approach,
   results, and their significance. The following are NOT abstracts: recipes, news,
   emails, code, a paper's introduction or conclusion section, reference lists, a
   table of contents, random prose, or a bare paper title.
3. If it is NOT an abstract, set "is_abstract" to false, explain why in "reason",
   and fill every score with 0 and every comment and the summary with an empty string.
4. If it IS an abstract, set "is_abstract" to true, briefly say why in "reason", and
   score it on each dimension from 1 (very poor) to 10 (excellent):
{_DIMENSION_GUIDE}
   For each dimension write ONE short sentence of concrete, actionable feedback in
   "comments". Then give an "overall_score" from 1 to 10 (your holistic judgement,
   not necessarily the average) and a 2-4 sentence "summary" that states the main
   strength, the main weakness, and the single most valuable improvement.

Be calibrated: a vague abstract with no numbers or concrete method deserves low
scores; a clear, specific, well-evidenced abstract deserves high scores.

Respond with ONLY a JSON object using exactly this shape:
{{
  "is_abstract": true,
  "reason": "string",
  "extracted_text": "string",
  "scores": {{{", ".join(f'"{k}": 0' for k, _ in DIMENSIONS)}}},
  "comments": {{{", ".join(f'"{k}": "string"' for k, _ in DIMENSIONS)}}},
  "overall_score": 0,
  "summary": "string"
}}
"""


class InputError(ValueError):
    """Raised when the input fails validation before or after the model call."""


def _client() -> OpenAI:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError(
            "LLM_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )
    return OpenAI(
        api_key=api_key,
        base_url=os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
    )


def model_name() -> str:
    return os.environ.get("LLM_MODEL", "deepseek-flash")


def word_count(text: str) -> int:
    return len(text.split())


def validate_text(text: str) -> str:
    """Local, zero-cost checks. Returns the cleaned text or raises InputError."""
    text = (text or "").strip()
    if not text:
        raise InputError("Input is empty. Paste an abstract or upload a file/image.")
    n = word_count(text)
    if n < MIN_WORDS:
        raise InputError(
            f"Input has {n} words; an abstract should have at least {MIN_WORDS}."
        )
    if n > MAX_WORDS:
        raise InputError(
            f"Input has {n} words; an abstract should have at most {MAX_WORDS}. "
            "Paste only the abstract, not the whole paper."
        )
    return text


def _image_to_data_url(path: str | Path) -> str:
    path = Path(path)
    mime, _ = mimetypes.guess_type(path.name)
    if mime not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        raise InputError("Unsupported image type. Use PNG, JPEG, GIF, or WebP.")
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{data}"


def _build_user_content(text: str | None, image_path: str | Path | None) -> Any:
    if image_path:
        return [
            {
                "type": "text",
                "text": "Transcribe the text in this image, then evaluate it as described.",
            },
            {"type": "image_url", "image_url": {"url": _image_to_data_url(image_path)}},
        ]
    return f"Evaluate the following text:\n\n{text}"


def score_abstract(
    text: str | None = None,
    image_path: str | Path | None = None,
    thinking: bool = False,
) -> dict[str, Any]:
    """Score an abstract given as text OR as an image. Exactly one must be provided.

    Returns the parsed JSON from the model plus a "_meta" block with usage info.
    Raises InputError for invalid input (including "not an abstract").
    """
    if bool(text) == bool(image_path):
        raise InputError("Provide exactly one input: text or an image.")
    if text:
        text = validate_text(text)

    response = _client().chat.completions.create(
        model=model_name(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_content(text, image_path)},
        ],
        response_format={"type": "json_object"},
        temperature=TEMPERATURE,
        extra_body={"thinking": {"type": "enabled" if thinking else "disabled"}},
    )

    message = response.choices[0].message
    try:
        result = json.loads(message.content or "")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model returned invalid JSON: {message.content!r}") from exc

    # Images skip the local word check, so enforce it on the transcription instead.
    if image_path:
        extracted = (result.get("extracted_text") or "").strip()
        if extracted:
            n = word_count(extracted)
            if n < MIN_WORDS or n > MAX_WORDS:
                raise InputError(
                    f"Text in the image has {n} words; expected {MIN_WORDS}-{MAX_WORDS}."
                )

    if not result.get("is_abstract"):
        raise InputError(
            "The input does not look like a paper abstract. "
            f"Model's reason: {result.get('reason', 'no reason given')}"
        )

    usage = response.usage
    result["_meta"] = {
        "model": response.model,
        "thinking": thinking,
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "reasoning_chars": len(getattr(message, "reasoning_content", "") or ""),
    }
    return result

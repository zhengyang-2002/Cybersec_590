"""Gradio web UI for the abstract scorer."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import gradio as gr

from abstract_scorer.scorer import (
    DIMENSIONS,
    MAX_WORDS,
    MIN_WORDS,
    InputError,
    model_name,
    score_abstract,
)

TEXT_FILE_TYPES = [".txt", ".md"]


def _read_text_file(path: str) -> str:
    p = Path(path)
    if p.suffix.lower() not in TEXT_FILE_TYPES:
        raise InputError(f"Unsupported file type '{p.suffix}'. Upload a .txt or .md file.")
    return p.read_text(encoding="utf-8", errors="replace")


def _format_result(result: dict[str, Any]):
    overall = result.get("overall_score", 0)
    rows = [
        [label, result["scores"].get(key, 0), result["comments"].get(key, "")]
        for key, label in DIMENSIONS
    ]
    meta = result.get("_meta", {})
    summary_md = (
        f"### Summary\n\n{result.get('summary', '')}\n\n"
        f"**Why this counts as an abstract:** {result.get('reason', '')}\n\n"
        f"<sub>Model: {meta.get('model')} · thinking: {'on' if meta.get('thinking') else 'off'} · "
        f"tokens in/out: {meta.get('prompt_tokens')}/{meta.get('completion_tokens')}</sub>"
    )
    return f"{overall} / 10", rows, summary_md, result


def run(text: str, file_path: str | None, image_path: str | None, thinking: bool):
    """Button handler. Picks whichever input the user supplied."""
    sources = [s for s in (text.strip() if text else "", file_path, image_path) if s]
    if len(sources) > 1:
        raise gr.Error("Please provide only one input: pasted text, a file, OR an image.")
    if not sources:
        raise gr.Error("No input. Paste an abstract, upload a .txt/.md file, or upload an image.")

    try:
        if image_path:
            result = score_abstract(image_path=image_path, thinking=thinking)
        else:
            content = _read_text_file(file_path) if file_path else text
            result = score_abstract(text=content, thinking=thinking)
    except InputError as exc:
        raise gr.Error(str(exc)) from exc
    except Exception as exc:  # network/model failure
        raise gr.Error(f"Scoring failed: {exc}") from exc

    return _format_result(result)


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Abstract Scorer") as demo:
        gr.Markdown(
            "# Abstract Scorer\n"
            "Paste a paper abstract, upload a text file, or upload a screenshot. "
            f"The app checks that the input really is an abstract ({MIN_WORDS}-{MAX_WORDS} words), "
            f"then asks **{model_name()}** for a structured review."
        )
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Tabs():
                    with gr.Tab("Paste text"):
                        text_in = gr.Textbox(
                            label="Abstract",
                            lines=12,
                            placeholder="Paste the abstract here...",
                        )
                    with gr.Tab("Upload file"):
                        file_in = gr.File(
                            label="Text file (.txt or .md)",
                            file_types=TEXT_FILE_TYPES,
                            type="filepath",
                        )
                    with gr.Tab("Upload image"):
                        image_in = gr.Image(
                            label="Screenshot of the abstract",
                            type="filepath",
                            sources=["upload", "clipboard"],
                        )
                thinking_in = gr.Checkbox(
                    label="Enable thinking mode (slower, more deliberate)", value=False
                )
                score_btn = gr.Button("Score", variant="primary")
            with gr.Column(scale=1):
                overall_out = gr.Label(label="Overall score (out of 10)")
                table_out = gr.Dataframe(
                    headers=["Dimension", "Score", "Feedback"],
                    datatype=["str", "number", "str"],
                    label="Per-dimension scores",
                    wrap=True,
                    interactive=False,
                )
                summary_out = gr.Markdown()
                with gr.Accordion("Raw JSON", open=False):
                    json_out = gr.JSON()

        score_btn.click(
            run,
            inputs=[text_in, file_in, image_in, thinking_in],
            outputs=[overall_out, table_out, summary_out, json_out],
        )
    return demo


def main() -> None:
    build_app().launch(
        server_name=os.environ.get("HOST", "0.0.0.0"),
        server_port=int(os.environ.get("PORT", "7860")),
    )


if __name__ == "__main__":
    main()

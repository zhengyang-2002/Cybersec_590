# Abstract Scorer

An LLM-powered reviewer for academic paper abstracts. Paste an abstract, upload a
`.txt`/`.md` file, or upload a screenshot, press **Score**, and get a structured
review: six 1-10 dimension scores with one-line feedback each, an overall score,
and a short summary. If the input is not actually an abstract, the app says so
and refuses to score it.

Built for CYBERSEC Assignment 1 to practice `uv`, Docker, and environment-based
configuration.

## How it works

1. **Local validation** (free, no model call): input must be 30-500 words.
2. **One model call** to an OpenAI-compatible endpoint (DeepSeek by default) with
   a system prompt that asks the model to (a) transcribe the image if one was
   given, (b) decide whether the text is a paper abstract, and (c) return scores,
   comments, and a summary as a single JSON object (JSON mode is enforced).
3. If the model says `is_abstract: false`, the UI shows an error with the reason.

Scoring dimensions: Problem & Motivation, Method Clarity, Results & Evidence,
Contribution & Novelty, Structure & Completeness, Language & Readability.

Options: a **thinking mode** checkbox toggles DeepSeek's chain-of-thought
reasoning (slower, more deliberate). Temperature is fixed at 0.2 in non-thinking
mode for consistent scores (the API ignores temperature in thinking mode).

## Configuration

All configuration comes from environment variables. No secrets live in the code.

```
cp .env.example .env
# then edit .env and set LLM_API_KEY
```

| Variable       | Default                    | Purpose                         |
| -------------- | -------------------------- | ------------------------------- |
| `LLM_API_KEY`  | (required)                 | API key                         |
| `LLM_BASE_URL` | `https://api.deepseek.com` | Any OpenAI-compatible endpoint  |
| `LLM_MODEL`    | `deepseek-flash`           | Model name                      |
| `PORT`         | `7860`                     | Port the web UI listens on      |

To use the Duke AI Gateway instead, set `LLM_BASE_URL=https://litellm.oit.duke.edu/v1`
and a model name available there.

## Run locally with uv

All commands below are run from this folder (`Assignment#1/abstract-scorer/`).

```
uv sync
uv run abstract-scorer
```

Open http://localhost:7860.

## Run with Docker

```
docker build -t abstract-scorer .
docker run --rm -p 7860:7860 --env-file .env abstract-scorer
```

Open http://localhost:7860.

## Project layout

```
pyproject.toml / uv.lock      reproducible dependencies
Dockerfile / .dockerignore    container build
.env.example                  configuration template (copy to .env)
src/abstract_scorer/scorer.py prompt, validation, and the model call
src/abstract_scorer/app.py    Gradio UI
samples/                      example inputs for testing and the demo
```

## Sample inputs

- `samples/good_abstract.txt` - a well-written abstract (scores ~9/10)
- `samples/weak_abstract.txt` - a vague abstract (scores ~3/10)
- `samples/not_abstract.txt` - a recipe; the app rejects it
- `samples/abstract_screenshot.png` - the good abstract as an image

## AI assistance disclosure

Project scaffolding (uv setup, Dockerfile, Gradio layout), the scoring prompt, the
scorer module, and this README were drafted with Claude Fable 5.1 via Claude Code
(VS Code extension) on Sep 16, 2026. I chose the application idea, defined the
input formats, word-count limits, scoring dimensions, and JSON output fields,
requested the thinking-mode toggle and low temperature, and reviewed and tested
the generated code against the DeepSeek API.

<!-- TODO: update the paragraph above with anything you change yourself before submitting. -->

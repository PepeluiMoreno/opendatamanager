# Chat with local Ollama model

This folder contains `chat_with_ollama.py`, a small interactive helper to send prompts to a local Ollama model (for example `deepseek-r1`).

Usage examples

- Interactive:

```bash
python scripts/chat_with_ollama.py --model deepseek-r1
```

- Single prompt (non-interactive):

```bash
python scripts/chat_with_ollama.py --model deepseek-r1 --prompt "Resume datos abiertos en 2 frases."
```

Notes

- The script calls the `ollama` CLI, so `ollama` must be installed and in your PATH.
- You can set the default model with the `OLLAMA_MODEL` environment variable.
- If your Ollama installation exposes an HTTP API (`ollama serve`), you can also use curl or a requests-based client; check `ollama help serve` for details.

#!/usr/bin/env python3
"""Interactive helper to chat with a local Ollama model.

Usage:
  - Interactive: `python scripts/chat_with_ollama.py --model deepseek-r1`
  - Single prompt: `python scripts/chat_with_ollama.py --model deepseek-r1 --prompt "Hola"`
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


def run_prompt(model: str, prompt: str) -> str:
    try:
        p = subprocess.run(["ollama", "run", model], input=prompt.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return "Error: ollama no encontrado. Asegúrate de que está instalado y en PATH."
    if p.returncode != 0:
        err = p.stderr.decode(errors="ignore")
        return f"Error ejecutando ollama (code {p.returncode}): {err}"
    return p.stdout.decode(errors="ignore").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Chat with a local Ollama model (deepseek).")
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "deepseek-r1"), help="Model name (default: deepseek-r1 or $OLLAMA_MODEL)")
    parser.add_argument("--prompt", help="If set, send a single prompt and exit")
    args = parser.parse_args()

    if args.prompt:
        out = run_prompt(args.model, args.prompt)
        print(out)
        return 0

    print(f"Conectando a modelo local: {args.model}. Escribe 'exit' o Ctrl-C para salir.")
    try:
        while True:
            try:
                prompt = input("You: ")
            except EOFError:
                break
            if not prompt:
                continue
            if prompt.strip().lower() in ("exit", "quit"):
                break
            out = run_prompt(args.model, prompt)
            print("Model:")
            print(out)
    except KeyboardInterrupt:
        print("\nSaliendo...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Modelo de lenguaje n-gram con backoff (Markov sobre palabras).

Por qué n-gram y no un Transformer (nanoGPT real):
  - Entrena en <1s sobre el corpus, sin GPU ni PyTorch.
  - Genera texto legible y permite muestrear con temperatura.
  - Calcula perplexity, la métrica clave para comparar modelos.
  - El PIPELINE pedagógico es idéntico al de nanoGPT: shards → train →
    sample → comparar sucio vs limpio. Para un Transformer, el alumno
    sustituiría esta clase por nanoGPT manteniendo la misma interfaz.

La demo clave (TRAIN-3) entrena DOS modelos —uno sobre el corpus crudo y
otro sobre el limpio— y compara perplexity + generaciones. El modelo
sucio aprende a generar HTML, mojibake y gibberish; el limpio genera
español coherente.
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict


class NgramLM:
    def __init__(self, n: int = 3) -> None:
        self.n = n
        self.ngrams: dict[tuple, Counter] = defaultdict(Counter)
        self.unigrams: Counter = Counter()
        self.vocab: set[str] = set()
        self.trained = False

    @staticmethod
    def tokenize(text: str) -> list[str]:
        # Tokenización palabra + puntuación básica (a nivel palabra para
        # que la generación sea legible).
        return re.findall(r"\w+|[.,;:¿?¡!]", text.lower())

    def train(self, texts: list[str]) -> dict:
        total_tokens = 0
        for text in texts:
            toks = ["<s>"] * (self.n - 1) + self.tokenize(text) + ["</s>"]
            total_tokens += len(toks)
            self.vocab.update(toks)
            for i in range(len(toks) - self.n + 1):
                context = tuple(toks[i:i + self.n - 1])
                target = toks[i + self.n - 1]
                self.ngrams[context][target] += 1
                self.unigrams[target] += 1
        self.trained = True
        return {
            "n": self.n,
            "total_tokens": total_tokens,
            "vocab_size": len(self.vocab),
            "num_contexts": len(self.ngrams),
        }

    def _prob(self, context: tuple, token: str) -> float:
        """Probabilidad con backoff a unigram + suavizado Laplace."""
        ctx_counter = self.ngrams.get(context)
        if ctx_counter and ctx_counter.total() > 0:
            return (ctx_counter[token] + 0.1) / (ctx_counter.total() + 0.1 * len(self.vocab))
        # backoff a unigram
        return (self.unigrams[token] + 0.1) / (self.unigrams.total() + 0.1 * len(self.vocab))

    def perplexity(self, texts: list[str]) -> float:
        """Perplexity sobre un conjunto de validación."""
        log_sum = 0.0
        n_tokens = 0
        for text in texts:
            toks = ["<s>"] * (self.n - 1) + self.tokenize(text) + ["</s>"]
            for i in range(self.n - 1, len(toks)):
                context = tuple(toks[i - self.n + 1:i])
                p = self._prob(context, toks[i])
                log_sum += math.log(max(p, 1e-12))
                n_tokens += 1
        if n_tokens == 0:
            return float("inf")
        return math.exp(-log_sum / n_tokens)

    def generate(self, prompt: str = "", max_tokens: int = 50, temperature: float = 0.8, seed: int = 42) -> str:
        rng = random.Random(seed)
        context = ["<s>"] * (self.n - 1)
        if prompt:
            context = (["<s>"] * (self.n - 1) + self.tokenize(prompt))[-(self.n - 1):]
        out = list(self.tokenize(prompt)) if prompt else []
        for _ in range(max_tokens):
            ctx = tuple(context)
            counter = self.ngrams.get(ctx)
            if not counter or counter.total() == 0:
                # backoff: muestrea de unigramas frecuentes
                counter = self.unigrams
            tokens = list(counter.keys())
            weights = [counter[t] ** (1.0 / max(0.1, temperature)) for t in tokens]
            total = sum(weights)
            if total == 0:
                break
            choice = rng.choices(tokens, weights=weights, k=1)[0]
            if choice == "</s>":
                break
            if choice not in ("<s>",):
                out.append(choice)
            context = (context + [choice])[-(self.n - 1):]
        # Reconstruir texto legible
        text = ""
        for tok in out:
            if tok in ".,;:?!":
                text = text.rstrip() + tok + " "
            else:
                text += tok + " "
        return text.strip()

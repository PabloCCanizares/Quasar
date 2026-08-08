"""BPE (Byte Pair Encoding) implementado desde cero.

Estilo Sennrich et al. 2016: entrena sobre una tabla de frecuencias de
palabras (no sobre el texto entero), lo que lo hace rápido y suficiente
para un laboratorio. Sin dependencia de HuggingFace tokenizers.

Uso:
    tok = BPETokenizer()
    tok.train(corpus_texts, num_merges=500)
    ids = tok.encode("hola mundo")
    text = tok.decode(ids)
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

# Marcador de fin de palabra (como en BPE clásico)
END = "</w>"


class BPETokenizer:
    def __init__(self) -> None:
        self.merges: list[tuple[str, str]] = []
        self.vocab: dict[str, int] = {}      # token string → id
        self.id_to_token: dict[int, str] = {}
        self.trained = False

    # --------------------------------------------------------
    @staticmethod
    def _word_freqs(texts: list[str]) -> dict[tuple[str, ...], int]:
        """Tabla de frecuencias: palabra (como tupla de chars + END) → count."""
        counter: Counter = Counter()
        for text in texts:
            for word in re.findall(r"\w+", text.lower()):
                counter[word] += 1
        word_freqs: dict[tuple[str, ...], int] = {}
        for word, freq in counter.items():
            symbols = tuple(list(word) + [END])
            word_freqs[symbols] = freq
        return word_freqs

    @staticmethod
    def _get_pair_counts(word_freqs: dict[tuple[str, ...], int]) -> Counter:
        pairs: Counter = Counter()
        for symbols, freq in word_freqs.items():
            for i in range(len(symbols) - 1):
                pairs[(symbols[i], symbols[i + 1])] += freq
        return pairs

    @staticmethod
    def _merge_pair(pair: tuple[str, str], word_freqs: dict) -> dict:
        merged = "".join(pair)
        new_freqs = {}
        for symbols, freq in word_freqs.items():
            new_symbols = []
            i = 0
            while i < len(symbols):
                if i < len(symbols) - 1 and symbols[i] == pair[0] and symbols[i + 1] == pair[1]:
                    new_symbols.append(merged)
                    i += 2
                else:
                    new_symbols.append(symbols[i])
                    i += 1
            new_freqs[tuple(new_symbols)] = freq
        return new_freqs

    # --------------------------------------------------------
    def train(self, texts: list[str], num_merges: int = 500) -> dict:
        """Entrena BPE. Devuelve estadísticas del entrenamiento."""
        word_freqs = self._word_freqs(texts)
        base_alphabet = set()
        for symbols in word_freqs:
            base_alphabet.update(symbols)

        self.merges = []
        for _ in range(num_merges):
            pair_counts = self._get_pair_counts(word_freqs)
            if not pair_counts:
                break
            best = pair_counts.most_common(1)[0][0]
            word_freqs = self._merge_pair(best, word_freqs)
            self.merges.append(best)

        # Construir vocabulario: alfabeto base + tokens fusionados
        tokens = sorted(base_alphabet) + ["".join(m) for m in self.merges]
        # Dedup preservando orden
        seen = set()
        ordered = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                ordered.append(t)
        self.vocab = {t: i for i, t in enumerate(ordered)}
        self.id_to_token = {i: t for t, i in self.vocab.items()}
        self.trained = True

        return {
            "num_merges": len(self.merges),
            "vocab_size": len(self.vocab),
            "base_alphabet_size": len(base_alphabet),
            "first_merges": ["".join(m) for m in self.merges[:20]],
        }

    # --------------------------------------------------------
    def _encode_word(self, word: str) -> list[str]:
        symbols = list(word) + [END]
        # Aplicar merges en orden
        merge_rank = {m: i for i, m in enumerate(self.merges)}
        while True:
            pairs = [(symbols[i], symbols[i + 1]) for i in range(len(symbols) - 1)]
            candidate = None
            best_rank = None
            for p in pairs:
                if p in merge_rank and (best_rank is None or merge_rank[p] < best_rank):
                    best_rank = merge_rank[p]
                    candidate = p
            if candidate is None:
                break
            merged = "".join(candidate)
            new_symbols = []
            i = 0
            while i < len(symbols):
                if i < len(symbols) - 1 and symbols[i] == candidate[0] and symbols[i + 1] == candidate[1]:
                    new_symbols.append(merged)
                    i += 2
                else:
                    new_symbols.append(symbols[i])
                    i += 1
            symbols = new_symbols
        return symbols

    def encode(self, text: str) -> list[int]:
        if not self.trained:
            raise RuntimeError("Tokenizer no entrenado")
        ids = []
        for word in re.findall(r"\w+", text.lower()):
            for tok in self._encode_word(word):
                if tok in self.vocab:
                    ids.append(self.vocab[tok])
        return ids

    def encode_tokens(self, text: str) -> list[str]:
        tokens = []
        for word in re.findall(r"\w+", text.lower()):
            tokens.extend(self._encode_word(word))
        return tokens

    def decode(self, ids: list[int]) -> str:
        toks = [self.id_to_token.get(i, "") for i in ids]
        return "".join(toks).replace(END, " ").strip()

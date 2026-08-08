"""Tests del modelo n-gram de LLM Lab (módulo puro)."""

import math

from quasar_ngram import NgramLM

CLEAN = [
    "la fotosíntesis es un proceso biológico fundamental",
    "el imperio romano fue una civilización antigua y poderosa",
    "la mecánica cuántica estudia las partículas subatómicas",
    "la economía de mercado se basa en oferta y demanda",
    "la teoría de la evolución explica la diversidad de especies",
] * 30

DIRTY = [
    "<ref>cita</ref> la fotosíntesis {{cite}} es un proceso",
    "lorem ipsum dolor sit amet biológico fundamental xxxxx",
    "la mecánica Ã¡ Ã© cuántica [[link]] partículas",
] * 30


def test_train_returns_stats():
    lm = NgramLM(n=3)
    stats = lm.train(CLEAN)
    assert stats["total_tokens"] > 0
    assert stats["vocab_size"] > 0
    assert stats["num_contexts"] > 0
    assert lm.trained is True


def test_perplexity_is_finite_and_positive():
    lm = NgramLM(n=3)
    lm.train(CLEAN)
    ppl = lm.perplexity(CLEAN[:5])
    assert math.isfinite(ppl)
    assert ppl > 0


def test_generate_non_empty():
    lm = NgramLM(n=3)
    lm.train(CLEAN)
    out = lm.generate(prompt="la", max_tokens=20, seed=1)
    assert isinstance(out, str)
    assert len(out) > 0


def test_dirty_vocab_contains_junk_tokens():
    """El corpus sucio aprende tokens basura (HTML, gibberish) que el limpio no."""
    clean_lm = NgramLM(n=3); clean_lm.train(CLEAN)
    dirty_lm = NgramLM(n=3); dirty_lm.train(DIRTY)
    # Tokens de basura presentes solo en el corpus sucio.
    junk = {"ref", "cite", "lorem", "ipsum", "link"}
    dirty_junk = junk & dirty_lm.vocab
    clean_junk = junk & clean_lm.vocab
    assert len(dirty_junk) > len(clean_junk)
    assert not clean_junk  # el corpus limpio no tiene ninguno


def test_deterministic_generation_with_seed():
    lm = NgramLM(n=3)
    lm.train(CLEAN)
    a = lm.generate(prompt="la", max_tokens=15, seed=42)
    b = lm.generate(prompt="la", max_tokens=15, seed=42)
    assert a == b


def test_tokenize_splits_punctuation():
    toks = NgramLM.tokenize("hola, mundo.")
    assert "," in toks and "." in toks

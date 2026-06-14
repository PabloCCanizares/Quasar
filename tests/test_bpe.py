"""Tests del tokenizer BPE de LLM Lab (módulo puro, sin dependencias)."""

from quasar_bpe import BPETokenizer, END


CORPUS = [
    "la fotosíntesis es un proceso biológico fundamental",
    "el imperio romano fue una civilización antigua",
    "la mecánica cuántica estudia las partículas",
    "la fotosíntesis convierte luz en energía química",
    "el proceso biológico de la fotosíntesis es fundamental",
] * 20


def test_train_produces_vocab():
    tok = BPETokenizer()
    stats = tok.train(CORPUS, num_merges=50)
    assert stats["num_merges"] <= 50
    assert stats["vocab_size"] > stats["base_alphabet_size"]
    assert tok.trained is True


def test_encode_decode_roundtrip():
    tok = BPETokenizer()
    tok.train(CORPUS, num_merges=100)
    text = "la fotosíntesis es un proceso"
    ids = tok.encode(text)
    decoded = tok.decode(ids)
    # El decode reconstruye las mismas palabras (a nivel de palabra)
    assert decoded.replace(" ", "") == text.replace(" ", "")


def test_encode_returns_valid_ids():
    tok = BPETokenizer()
    tok.train(CORPUS, num_merges=80)
    ids = tok.encode("la mecánica cuántica")
    assert all(isinstance(i, int) for i in ids)
    assert all(0 <= i < len(tok.vocab) for i in ids)


def test_more_merges_means_fewer_tokens():
    """Más merges → mejor compresión (menos tokens por texto)."""
    text = "la fotosíntesis es un proceso biológico fundamental"
    tok_few = BPETokenizer(); tok_few.train(CORPUS, num_merges=10)
    tok_many = BPETokenizer(); tok_many.train(CORPUS, num_merges=200)
    assert len(tok_many.encode(text)) <= len(tok_few.encode(text))


def test_end_marker_in_tokens():
    tok = BPETokenizer()
    tok.train(CORPUS, num_merges=50)
    tokens = tok.encode_tokens("fotosíntesis")
    # La última subpalabra debe llevar el marcador de fin
    assert any(END in t for t in tokens)


def test_empty_text():
    tok = BPETokenizer()
    tok.train(CORPUS, num_merges=20)
    assert tok.encode("") == []

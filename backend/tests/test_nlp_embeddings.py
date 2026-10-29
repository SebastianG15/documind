import numpy as np
import pytest

from src.nlp.embeddings import EmbeddingEngine


def test_embedding_dimensions_and_unit_norm():
    engine = EmbeddingEngine()
    text = "Factura electronica F001-0004523 emitida por DISTRIBUIDORA INDUSTRIAL S.A.C."
    vector = engine.embed_text(text)

    assert isinstance(vector, list)
    assert len(vector) == 384
    # All elements must be floats
    assert all(isinstance(val, float) for val in vector)

    # Unit normalization check: L2 norm should be ~ 1.0
    arr = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    assert abs(norm - 1.0) < 0.01


def test_batch_embedding_generation():
    engine = EmbeddingEngine()
    texts = [
        "VALVULA DE CONTROL DE 1/2 PULGADA",
        "MANOMETRO DE PRESION DIFERENCIAL",
    ]
    vectors = engine.embed_batch(texts)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384


def test_semantic_similarity_ranking():
    engine = EmbeddingEngine()
    query = "Comprobante de compra de valvulas de acero"
    similar_text = "Factura por adquisicion de valvulas de control para planta"
    unrelated_text = "Receta medica de amoxicilina e indicaciones de farmacia"

    q_vec = np.array(engine.embed_text(query), dtype=np.float32)
    sim_vec = np.array(engine.embed_text(similar_text), dtype=np.float32)
    unrel_vec = np.array(engine.embed_text(unrelated_text), dtype=np.float32)

    cos_sim_similar = float(np.dot(q_vec, sim_vec))
    cos_sim_unrelated = float(np.dot(q_vec, unrel_vec))

    assert cos_sim_similar > cos_sim_unrelated
    assert cos_sim_similar > 0.50
    assert cos_sim_unrelated < 0.35


def test_empty_text_returns_zero_vector():
    engine = EmbeddingEngine()
    vector = engine.embed_text("")

    assert len(vector) == 384
    assert all(val == 0.0 for val in vector)

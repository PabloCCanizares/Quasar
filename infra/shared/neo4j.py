"""Neo4j compartido — driver y helpers de escritura best-effort.

Las apps usan `neo4j_write(cypher, params)` para sincronizar eventos en
tiempo real (no crítico). Las cargas masivas las hace Spark con el conector
oficial, no este helper.
"""

from __future__ import annotations

from infra.shared.config_base import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD


def neo4j_write(cypher: str, params: dict | None = None) -> None:
    """Ejecuta una escritura en Neo4j. Falla silenciosamente si no hay conexión.

    Pensado para sync live (eventos de la app web → grafo). Si Neo4j no está
    disponible, la app sigue funcionando sin el grafo actualizado.
    """
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run(cypher, params or {})
        driver.close()
    except Exception:
        pass  # Neo4j es opcional para live sync — best-effort

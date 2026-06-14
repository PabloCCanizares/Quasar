"""Helper compartido para queries Cypher contra Neo4j.

Centralizado para que los bloques basic/intermediate/advanced (y sus scaffolds)
no duplican la conexion ni el manejo de errores.
"""

from src.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


def neo4j_query(cypher: str, params: dict = None):
    """Ejecuta una query Cypher y devuelve list[dict].

    Si Neo4j no esta disponible, devuelve {"error": ..., "available": False}
    para que el frontend pueda degradar la UI sin romperse.
    """
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run(cypher, params or {})
            records = [dict(r) for r in result]
        driver.close()
        return records
    except Exception as e:
        return {"error": str(e), "available": False}


def exercise_placeholder(exercise_id: str, hint: str = ""):
    """Respuesta estandar para endpoints scaffold (bloque sin desbloquear).

    Es un dict con la misma forma que un error de neo4j_query() para que el
    frontend lo maneje con la rama de error existente.
    """
    restart_hint = "Despues de implementar el ejercicio ejecuta: docker compose restart app"
    full_hint = f"{hint}. {restart_hint}" if hint else restart_hint
    return {
        "error": f"Ejercicio {exercise_id} sin resolver",
        "exercise": exercise_id,
        "hint": full_hint,
        "available": False,
    }

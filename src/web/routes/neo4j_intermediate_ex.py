"""Ejercicios Neo4j INTERMEDIATE - scaffold del alumno.

Este archivo es el punto de partida del bloque INTERMEDIATE cuando LAB_NEO4J
esta vacio. La aplicacion importa estos endpoints y muestra "ejercicio sin
resolver" hasta que sustituyas cada `exercise_placeholder(...)` por una llamada
a `neo4j_query(...)` con tu consulta Cypher.

Objetivo del bloque:
  - Combinar varios patrones MATCH.
  - Trabajar con collect, DISTINCT y agregaciones cruzadas.
  - Usar OPTIONAL MATCH cuando una relacion puede no existir.

Flujo de trabajo:
  1. Implementa las funciones marcadas como ejercicio en este archivo.
  2. Ejecuta `docker compose restart app` para recargar FastAPI.
  3. Recarga la pestaña Neo4j en la web.

No uses `./lab.sh unlock neo4j intermediate` salvo que seas profesor y quieras
cargar la solucion oficial en `neo4j_intermediate.py`.
"""

from fastapi import APIRouter

from src.web.routes._neo4j_helper import neo4j_query, exercise_placeholder

router = APIRouter(prefix="/api/analytics/neo4j", tags=["analytics-neo4j"])


@router.get("/bridges")
async def neo4j_bridges(limit: int = 10):
    """
    EJERCICIO Neo4j-intermediate-1: Usuarios puente entre comunidades.

    Devuelve los `limit` usuarios que pertenecen al menos a 3 comunidades
    de hashtag distintas, ordenados por numero de hashtags y luego por
    seguidores entrantes.

    Cada registro:
        {id, username, tags, tag_count, followers}

      - tags      = lista de nombres de hashtag a los que pertenece
      - tag_count = numero de hashtags distintos
      - followers = numero de :FOLLOWS entrantes

    Pistas:
      - (u:User)-[:INTERESTED_IN]->(h:Hashtag), agrupa por u y collect(h.name).
      - Filtra con WHERE tag_count >= 3.
      - Despues haz un segundo MATCH para contar followers entrantes.
    """
    return exercise_placeholder("Neo4j-intermediate-1",
        "Agrupa hashtags por usuario, filtra >= 3, anade followers")


@router.get("/mutual-interests")
async def neo4j_mutual_interests(user_id: str, limit: int = 5):
    """
    EJERCICIO Neo4j-intermediate-2: Usuarios con mas intereses en comun.

    Dado un usuario `user_id`, encuentra los `limit` usuarios que comparten
    mas hashtags con el.

    Cada registro:
        {id, username, shared_tags, shared_count}

    Pistas:
      - Patron: (me)-[:INTERESTED_IN]->(h)<-[:INTERESTED_IN]-(other).
      - Excluye me <> other.
      - collect(h.name) AS shared_tags, count(h) AS shared_count.
    """
    return exercise_placeholder("Neo4j-intermediate-2",
        "Patron en V para hashtags compartidos")


@router.get("/hashtag-graph")
async def neo4j_hashtag_graph(limit: int = 20):
    """
    EJERCICIO Neo4j-intermediate-3: Grafo de co-ocurrencia de hashtags.

    Devuelve los `limit` pares de hashtags (h1, h2) que mas usuarios usan
    juntos. Evita pares repetidos (h1 con h2 igual a h2 con h1).

    Cada registro:
        {tag1, tag2, shared_users}

    Pistas:
      - Doble patron: (u)-[:INTERESTED_IN]->(h1) y (u)-[:INTERESTED_IN]->(h2).
      - Para evitar duplicados: WHERE id(h1) < id(h2).
      - count(u) AS shared_users.
    """
    return exercise_placeholder("Neo4j-intermediate-3",
        "Doble MATCH al mismo usuario, id(h1) < id(h2)")


@router.get("/my-communities")
async def neo4j_my_communities(user_id: str, limit: int = 8):
    """
    EJERCICIO Neo4j-intermediate-4: Comunidades del usuario.

    Para el usuario `user_id`, devuelve los `limit` hashtags a los que
    pertenece, junto con tamano de la comunidad y los 5 miembros mas
    relevantes.

    Cada registro:
        {hashtag, size, top_members}

    donde top_members es una lista de hasta 5 dicts:
        {id, username, followers}

    Pistas:
      - Patron en V desde me: (me)-[:INTERESTED_IN]->(h)<-[:INTERESTED_IN]-(other).
      - collect(DISTINCT {id, username, followers}) AS members.
      - members[0..5] AS top_members.
    """
    return exercise_placeholder("Neo4j-intermediate-4",
        "Para cada hashtag de me, recoge miembros y corta a 5")


@router.get("/community-overlap")
async def neo4j_community_overlap(user_id: str):
    """
    EJERCICIO Neo4j-intermediate-5: Solapamiento de comunidades.

    Para los 15 usuarios con mas hashtags compartidos con `user_id`, indica
    si me sigue, si yo le sigo y la lista de hashtags compartidos.

    Cada registro:
        {id, username, shared, overlap, i_follow, follows_me}

    Pistas:
      - Empieza con el patron en V de hashtags compartidos.
      - Usa OPTIONAL MATCH para detectar las relaciones :FOLLOWS sin
        forzar que existan.
      - count(me) > 0 AS i_follow para convertir presencia en booleano.
    """
    return exercise_placeholder("Neo4j-intermediate-5",
        "Combina patron en V + OPTIONAL MATCH para los follows")

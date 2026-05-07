"""Bloque INTERMEDIATE de Cypher (SOLUCIONES).

Endpoints incluidos:
  - /api/analytics/neo4j/bridges
  - /api/analytics/neo4j/mutual-interests
  - /api/analytics/neo4j/hashtag-graph
  - /api/analytics/neo4j/my-communities
  - /api/analytics/neo4j/community-overlap

Concepto que ensena: multi-MATCH, joins entre patrones, collect, agregaciones
sobre sub-grafos.

Si LAB_NEO4J no contiene 'intermediate', se importa neo4j_intermediate_ex.py
(scaffolds) en su lugar.
"""

from fastapi import APIRouter

from src.web.routes._neo4j_helper import neo4j_query

router = APIRouter(prefix="/api/analytics/neo4j", tags=["analytics-neo4j"])


@router.get("/bridges")
async def neo4j_bridges(limit: int = 10):
    """Usuarios puente: conectan comunidades diferentes (alto betweenness)."""
    return neo4j_query("""
        MATCH (u:User)-[:INTERESTED_IN]->(h:Hashtag)
        WITH u, collect(DISTINCT h.name) AS tags, count(DISTINCT h) AS tag_count
        WHERE tag_count >= 3
        MATCH (u)<-[:FOLLOWS]-(f)
        WITH u, tags, tag_count, count(f) AS followers
        ORDER BY tag_count DESC, followers DESC
        LIMIT $limit
        RETURN u.id AS id, u.username AS username, tags, tag_count, followers
    """, {"limit": limit})


@router.get("/mutual-interests")
async def neo4j_mutual_interests(user_id: str, limit: int = 5):
    """Usuarios con mas intereses en comun con el usuario dado."""
    return neo4j_query("""
        MATCH (me:User {id: $uid})-[:INTERESTED_IN]->(h:Hashtag)<-[:INTERESTED_IN]-(other:User)
        WHERE me <> other
        WITH other, collect(h.name) AS shared_tags, count(h) AS shared_count
        ORDER BY shared_count DESC
        LIMIT $limit
        RETURN other.id AS id, other.username AS username,
               shared_tags, shared_count
    """, {"uid": user_id, "limit": limit})


@router.get("/hashtag-graph")
async def neo4j_hashtag_graph(limit: int = 20):
    """Grafo de co-ocurrencia de hashtags (hashtags que aparecen juntos)."""
    return neo4j_query("""
        MATCH (u:User)-[:INTERESTED_IN]->(h1:Hashtag),
              (u)-[:INTERESTED_IN]->(h2:Hashtag)
        WHERE id(h1) < id(h2)
        WITH h1.name AS tag1, h2.name AS tag2, count(u) AS shared_users
        ORDER BY shared_users DESC
        LIMIT $limit
        RETURN tag1, tag2, shared_users
    """, {"limit": limit})


@router.get("/my-communities")
async def neo4j_my_communities(user_id: str, limit: int = 8):
    """Comunidades (hashtags) a las que pertenece el usuario y vecinos."""
    return neo4j_query("""
        MATCH (me:User {id: $uid})-[:INTERESTED_IN]->(h:Hashtag)<-[:INTERESTED_IN]-(other:User)
        WHERE me <> other
        WITH h, collect(DISTINCT {id: other.id, username: other.username,
             followers: other.followers_count}) AS members,
             count(DISTINCT other) AS size
        ORDER BY size DESC
        LIMIT $limit
        RETURN h.name AS hashtag, size,
               members[0..5] AS top_members
    """, {"uid": user_id, "limit": limit})


@router.get("/community-overlap")
async def neo4j_community_overlap(user_id: str):
    """Cuantas comunidades comparte el usuario con otros usuarios cercanos."""
    return neo4j_query("""
        MATCH (me:User {id: $uid})-[:INTERESTED_IN]->(h:Hashtag)<-[:INTERESTED_IN]-(other:User)
        WHERE me <> other
        WITH other, collect(h.name) AS shared, count(h) AS overlap
        ORDER BY overlap DESC
        LIMIT 15
        OPTIONAL MATCH (me:User {id: $uid})-[:FOLLOWS]->(other)
        WITH other, shared, overlap, count(me) > 0 AS i_follow
        OPTIONAL MATCH (other)-[:FOLLOWS]->(me2:User {id: $uid})
        RETURN other.id AS id, other.username AS username,
               shared, overlap, i_follow,
               count(me2) > 0 AS follows_me
    """, {"uid": user_id})

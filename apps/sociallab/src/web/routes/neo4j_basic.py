"""Bloque BASIC de Cypher (SOLUCIONES).

Endpoints incluidos:
  - /api/analytics/neo4j/stats
  - /api/analytics/neo4j/influencers
  - /api/analytics/neo4j/communities

Concepto que enseña: MATCH simple + count + ORDER BY.

Si LAB_NEO4J no contiene 'basic', el agregador analytics.py importa
neo4j_basic_ex.py (scaffolds) en lugar de este archivo.
"""

from fastapi import APIRouter

from src.web.routes._neo4j_helper import neo4j_query

router = APIRouter(prefix="/api/analytics/neo4j", tags=["analytics-neo4j"])


@router.get("/stats")
async def neo4j_stats():
    """Estadisticas generales del grafo."""
    return neo4j_query("""
        MATCH (u:User) WITH count(u) AS users
        MATCH (h:Hashtag) WITH users, count(h) AS hashtags
        MATCH ()-[f:FOLLOWS]->() WITH users, hashtags, count(f) AS follows
        MATCH ()-[i:INTERESTED_IN]->()
        RETURN users, hashtags, follows, count(i) AS interests
    """)


@router.get("/influencers")
async def neo4j_influencers(limit: int = 10):
    """Top usuarios por numero de seguidores (PageRank simplificado)."""
    return neo4j_query("""
        MATCH (u:User)<-[:FOLLOWS]-(follower)
        WITH u, count(follower) AS followers
        ORDER BY followers DESC
        LIMIT $limit
        RETURN u.id AS id, u.username AS username, u.display_name AS name,
               followers, u.posts_count AS posts
    """, {"limit": limit})


@router.get("/communities")
async def neo4j_communities(limit: int = 10):
    """Comunidades por hashtag: hashtags que mas usuarios comparten."""
    return neo4j_query("""
        MATCH (h:Hashtag)<-[:INTERESTED_IN]-(u:User)
        WITH h, count(u) AS users
        ORDER BY users DESC
        LIMIT $limit
        RETURN h.name AS hashtag, users
    """, {"limit": limit})

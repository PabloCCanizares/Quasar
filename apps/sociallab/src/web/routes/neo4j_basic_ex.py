"""Ejercicios Neo4j BASIC - scaffold del alumno.

Este archivo es el punto de partida del bloque BASIC cuando LAB_NEO4J esta
vacio. La aplicacion importa estos endpoints y muestra "ejercicio sin resolver"
hasta que sustituyas cada `exercise_placeholder(...)` por una llamada a
`neo4j_query(...)` con tu consulta Cypher.

Objetivo del bloque:
  - Leer patrones simples con MATCH.
  - Contar nodos y relaciones.
  - Ordenar resultados con ORDER BY y LIMIT.

Flujo de trabajo:
  1. Implementa las funciones marcadas como ejercicio en este archivo.
  2. Ejecuta `docker compose restart app` para recargar FastAPI.
  3. Recarga la pestaña Neo4j en la web.

No uses `./lab.sh unlock neo4j basic` salvo que seas profesor y quieras cargar
la solucion oficial en `neo4j_basic.py`.
"""

from fastapi import APIRouter

from src.web.routes._neo4j_helper import exercise_placeholder, neo4j_query

router = APIRouter(prefix="/api/analytics/neo4j", tags=["analytics-neo4j"])


@router.get("/stats")
async def neo4j_stats():
    """
    EJERCICIO Neo4j-basic-1: Estadisticas generales del grafo.

    Devuelve un unico registro con los conteos:
        {users, hashtags, follows, interests}

    - users     : numero de nodos :User
    - hashtags  : numero de nodos :Hashtag
    - follows   : numero de relaciones :FOLLOWS
    - interests : numero de relaciones :INTERESTED_IN

    Pistas:
      - Encadena varios MATCH usando WITH para acumular contadores entre ellos.
      - count(x) cuenta filas; count(DISTINCT x) cuenta valores unicos.
    """
    return exercise_placeholder("Neo4j-basic-1",
        "Cuenta nodos User/Hashtag y relaciones FOLLOWS/INTERESTED_IN")
    # TODO: Sustituye lo de arriba por:
    # return neo4j_query("""
    #     MATCH (u:User) WITH count(u) AS users
    #     ...
    # """)


@router.get("/influencers")
async def neo4j_influencers(limit: int = 10):
    """
    EJERCICIO Neo4j-basic-2: Top influencers por numero de seguidores.

    Devuelve los `limit` usuarios con mas relaciones :FOLLOWS entrantes.

    Cada registro:
        {id, username, name, followers, posts}

    donde:
      - id        = u.id
      - username  = u.username
      - name      = u.display_name
      - followers = numero de seguidores entrantes
      - posts     = u.posts_count

    Pistas:
      - Usa el patron (u:User)<-[:FOLLOWS]-(follower) para contar entrantes.
      - WITH u, count(follower) AS followers permite ordenar luego.
      - ORDER BY followers DESC LIMIT $limit.
    """
    return exercise_placeholder("Neo4j-basic-2",
        "Cuenta los :FOLLOWS entrantes y ordena DESC")


@router.get("/communities")
async def neo4j_communities(limit: int = 10):
    """
    EJERCICIO Neo4j-basic-3: Comunidades por hashtag.

    Lista los `limit` hashtags con mas usuarios :INTERESTED_IN.

    Cada registro:
        {hashtag, users}

    Pistas:
      - (h:Hashtag)<-[:INTERESTED_IN]-(u:User) → cuenta cuantos User
        apuntan a cada Hashtag.
      - Devuelve h.name como hashtag y count(u) como users.
    """
    return exercise_placeholder("Neo4j-basic-3",
        "Cuenta usuarios por hashtag y ordena DESC")

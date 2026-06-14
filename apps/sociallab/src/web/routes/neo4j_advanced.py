"""Bloque ADVANCED de Cypher (SOLUCIONES).

Endpoints incluidos:
  - /api/analytics/neo4j/shortest-path
  - /api/analytics/neo4j/ego-network
  - /api/analytics/neo4j/reach
  - /api/analytics/neo4j/famous-distances

Concepto que ensena: shortestPath, traversals con [*1..n], ego networks,
sub-grafos derivados de un nodo central.

Si LAB_NEO4J no contiene 'advanced', se importa neo4j_advanced_ex.py
(scaffolds) en su lugar.
"""

from uuid import uuid4

from fastapi import APIRouter

from src.web.database import get_db, neo4j_write
from src.web.routes._neo4j_helper import neo4j_query

router = APIRouter(prefix="/api/analytics/neo4j", tags=["analytics-neo4j"])
db = get_db()


@router.get("/shortest-path")
async def neo4j_shortest_path(from_user: str, to_user: str):
    """Camino mas corto entre dos usuarios via FOLLOWS.

    Acepta tanto IDs internos (`u_...`) como usernames (`rosalia`, `ibai`).
    """
    return neo4j_query("""
        MATCH (a:User), (b:User)
        WHERE (a.id = $from OR a.username = $from)
          AND (b.id = $to OR b.username = $to)
        MATCH path = shortestPath((a)-[:FOLLOWS*..6]-(b))
        RETURN a.id AS from_id, a.username AS from_username,
               b.id AS to_id, b.username AS to_username,
               [n IN nodes(path) | {id: n.id, username: n.username}] AS path,
               length(path) AS distance
    """, {"from": from_user, "to": to_user})


@router.get("/ego-network")
async def neo4j_ego_network(user_id: str, depth: int = 2, limit: int = 40):
    """Red ego del usuario: nodos y aristas a N saltos."""
    records = neo4j_query("""
        MATCH path = (me:User {id: $uid})-[:FOLLOWS*1..""" + str(min(depth, 3)) + """]-(other:User)
        WITH me, other, min(length(path)) AS dist
        ORDER BY dist, other.followers_count DESC
        LIMIT $limit
        WITH me, collect({id: other.id, username: other.username,
             name: other.display_name, followers: other.followers_count,
             posts: other.posts_count, dist: dist}) AS neighbors
        WITH me, neighbors,
             [n IN neighbors | n.id] AS ids
        UNWIND neighbors AS n
        WITH me, neighbors, ids, n
        OPTIONAL MATCH (a:User {id: n.id})-[f:FOLLOWS]->(b:User)
        WHERE b.id IN ids OR b.id = me.id
        WITH me, neighbors,
             collect(DISTINCT {source: a.id, target: b.id}) AS edges
        RETURN {id: me.id, username: me.username, name: me.display_name,
                followers: me.followers_count, posts: me.posts_count, dist: 0} AS center,
               neighbors, edges
    """, {"uid": user_id, "limit": limit})
    if isinstance(records, dict) and records.get("error"):
        return records
    if not records:
        return {"center": None, "neighbors": [], "edges": []}
    r = records[0]
    return {"center": r["center"], "neighbors": r["neighbors"], "edges": r["edges"]}


@router.get("/reach")
async def neo4j_reach(user_id: str):
    """Quien te conoce: cuantas personas llegan a ti en N saltos.
    Basado en la teoria de los 6 grados de separacion."""
    return neo4j_query("""
        MATCH (me:User {id: $uid})
        OPTIONAL MATCH (me)<-[:FOLLOWS*1..1]-(h1:User)
        WITH me, count(DISTINCT h1) AS hop1
        OPTIONAL MATCH (me)<-[:FOLLOWS*1..2]-(h2:User)
        With me, hop1, count(DISTINCT h2) AS hop2
        OPTIONAL MATCH (me)<-[:FOLLOWS*1..3]-(h3:User)
        RETURN hop1, hop2, count(DISTINCT h3) AS hop3
    """, {"uid": user_id})


@router.get("/famous-distances")
async def neo4j_famous_distances(user_id: str):
    """A cuantos saltos te conocen los famosos (entrante: ellos -> tu)."""
    famous_usernames = [
        "elonmusk", "taylorswift", "leomessi", "ibaboreal",
        "rosalia", "auronplay", "shakira", "jbalvin",
    ]
    return neo4j_query("""
        MATCH (me:User {id: $uid})
        UNWIND $names AS fname
        MATCH (famous:User {username: fname})
        OPTIONAL MATCH p = shortestPath((famous)-[:FOLLOWS*..6]->(me))
        RETURN famous.username AS username,
               famous.display_name AS display_name,
               famous.followers_count AS followers,
               CASE WHEN p IS NULL THEN -1 ELSE length(p) END AS distance
        ORDER BY distance
    """, {"uid": user_id, "names": famous_usernames})


@router.post("/demo-followers/{user_id}")
async def neo4j_demo_followers(user_id: str):
    """Crea una audiencia demo para que el radar de alcance tenga 3 anillos."""
    target = await db.users.find_one({"_id": user_id})
    if not target:
        return {"error": "User not found"}

    ring1_names = [
        "ibai", "shakira", "rosalia", "leomessi",
        "auronplay", "elrubius", "taylorswift", "elonmusk",
    ]
    ring2_names = [
        "knekro", "thegrefg", "willyrex", "vegetta777",
        "cristininik", "badbunny", "karolg", "bizarrap",
        "nasa", "mit", "stanford", "feifeili",
    ]
    ring3_names = [
        "alexelcapo", "illojuan", "gemita", "misterjagger",
        "mangelrogel", "mkbhd", "lexfridman", "sama",
        "yannlecun", "greta", "cern", "jbalvin",
    ]

    usernames = ring1_names + ring2_names + ring3_names
    users = {}
    async for doc in db.users.find({"username": {"$in": usernames}}):
        users[doc["username"]] = doc

    desired_edges = []
    for name in ring1_names:
        if name in users and users[name]["_id"] != user_id:
            desired_edges.append((users[name], target))

    for idx, name in enumerate(ring2_names):
        parent = users.get(ring1_names[idx % len(ring1_names)])
        child = users.get(name)
        if child and parent and child["_id"] != parent["_id"]:
            desired_edges.append((child, parent))

    for idx, name in enumerate(ring3_names):
        parent = users.get(ring2_names[idx % len(ring2_names)])
        child = users.get(name)
        if child and parent and child["_id"] != parent["_id"]:
            desired_edges.append((child, parent))

    created = 0
    edges_for_neo4j = []
    for follower, following in desired_edges:
        follower_id = follower["_id"]
        following_id = following["_id"]
        existing = await db.follows.find_one({
            "follower_id": follower_id,
            "following_id": following_id,
        })
        if not existing:
            await db.follows.insert_one({
                "_id": f"fw_demo_{uuid4().hex[:8]}",
                "follower_id": follower_id,
                "following_id": following_id,
                "origin": "live",
            })
            await db.users.update_one({"_id": follower_id}, {"$inc": {"following_count": 1}})
            await db.users.update_one({"_id": following_id}, {"$inc": {"followers_count": 1}})
            created += 1

        edges_for_neo4j.append({
            "follower_id": follower_id,
            "follower_username": follower.get("username", follower_id),
            "follower_name": follower.get("display_name") or follower.get("username", follower_id),
            "following_id": following_id,
            "following_username": following.get("username", following_id),
            "following_name": following.get("display_name") or following.get("username", following_id),
        })

    neo4j_write("""
        UNWIND $edges AS e
        MERGE (a:User {id: e.follower_id})
        SET a.username = e.follower_username,
            a.display_name = e.follower_name
        MERGE (b:User {id: e.following_id})
        SET b.username = e.following_username,
            b.display_name = e.following_name
        MERGE (a)-[:FOLLOWS]->(b)
    """, {"edges": edges_for_neo4j})

    return {
        "created_edges": created,
        "total_edges": len(edges_for_neo4j),
        "ring1": len([u for u in ring1_names if u in users]),
        "ring2": len([u for u in ring2_names if u in users]),
        "ring3": len([u for u in ring3_names if u in users]),
    }

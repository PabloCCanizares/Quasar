"""Ejercicios Neo4j ADVANCED - scaffold del alumno.

Este archivo es el punto de partida del bloque ADVANCED cuando LAB_NEO4J esta
vacio. La aplicacion importa estos endpoints y muestra "ejercicio sin resolver"
hasta que sustituyas cada `exercise_placeholder(...)` por una llamada a
`neo4j_query(...)` con tu consulta Cypher.

Objetivo del bloque:
  - Resolver consultas de caminos con relaciones de longitud variable.
  - Construir subgrafos ego para visualizacion.
  - Usar shortestPath y proyecciones de nodos dentro de un path.

Flujo de trabajo:
  1. Implementa las funciones marcadas como ejercicio en este archivo.
  2. Ejecuta `docker compose restart app` para recargar FastAPI.
  3. Recarga la pestaña Neo4j en la web.

No uses `./lab.sh unlock neo4j advanced` salvo que seas profesor y quieras
cargar la solucion oficial en `neo4j_advanced.py`.
"""

from fastapi import APIRouter

from src.web.routes._neo4j_helper import exercise_placeholder, neo4j_query

router = APIRouter(prefix="/api/analytics/neo4j", tags=["analytics-neo4j"])


@router.get("/shortest-path")
async def neo4j_shortest_path(from_user: str, to_user: str):
    """
    EJERCICIO Neo4j-advanced-1: Camino mas corto entre dos usuarios.

    Encuentra el camino mas corto via :FOLLOWS (en cualquier direccion)
    entre dos usuarios, aceptando id interno (`u_...`) o username
    (`rosalia`, `ibai`, etc.), con un maximo de 6 saltos.

    Devuelve un unico registro:
        {path, distance}

      - path     = lista de {id, username} en orden del camino
      - distance = longitud del camino (numero de aristas)

    Pistas:
      - shortestPath((a)-[:FOLLOWS*..6]-(b)) — sin direccion.
      - Para resolver id o username: MATCH (a:User), (b:User)
        WHERE (a.id = $from OR a.username = $from) ...
      - [n IN nodes(path) | {id: n.id, username: n.username}] para
        proyectar cada nodo del camino.
      - length(path) da el numero de aristas.
    Compruebalo:
      - distance tiene que ser exactamente len(path) - 1: un camino de tres
        nodos son dos saltos. Si te cuadran, seguramente estas devolviendo
        nodos en vez de aristas.
      - El primer y el ultimo elemento de path tienen que ser los usuarios
        que pediste, en ese orden.
      - Prueba con un usuario contra si mismo: la distancia deberia ser 0.
      - Como el camino va sin direccion, buscar de A a B y de B a A tiene
        que dar la misma distancia. Si no, se te ha colado una flecha.
    """
    return exercise_placeholder("Neo4j-advanced-1",
        "shortestPath con FOLLOWS*..6 sin direccion")


@router.get("/ego-network")
async def neo4j_ego_network(user_id: str, depth: int = 2, limit: int = 40):
    """
    EJERCICIO Neo4j-advanced-2: Red ego del usuario.

    Para el usuario `user_id`, devuelve su red ego hasta profundidad
    `depth` (max 3): nodos vecinos y aristas FOLLOWS entre ellos.

    Devuelve un unico dict con:
        {center, neighbors, edges}

      - center    = {id, username, name, followers, posts, dist: 0}
      - neighbors = lista de nodos con su distancia minima al centro
      - edges     = lista de {source, target} solo entre los neighbors

    Pistas:
      - MATCH path = (me)-[:FOLLOWS*1..N]-(other) y agrupa por other con
        min(length(path)) AS dist.
      - Limita por dist y followers_count antes de pasar a buscar aristas.
      - Para las aristas: OPTIONAL MATCH (a)-[:FOLLOWS]->(b) WHERE
        b.id IN ids del subgrafo.
    Compruebalo:
      - El centro no puede aparecer tambien entre los neighbors.
      - Toda arista tiene que unir dos nodos que esten en la lista de
        neighbors: si alguna apunta fuera, no la has filtrado al subgrafo.
      - Sube `depth` de 1 a 2: los vecinos solo pueden aumentar, nunca
        disminuir. Si bajan, estas sobrescribiendo la distancia minima en
        vez de quedarte con la menor.
      - Con depth=1 todos los neighbors deben tener dist = 1.
    """
    return exercise_placeholder("Neo4j-advanced-2",
        "Path variable + agrupacion por dist minima + aristas internas")


@router.get("/reach")
async def neo4j_reach(user_id: str):
    """
    EJERCICIO Neo4j-advanced-3: Alcance entrante (quien te conoce).

    Para el usuario `user_id`, cuenta cuantos usuarios distintos llegan
    a el siguiendo :FOLLOWS hacia adentro en 1, 2 y 3 saltos.

    Devuelve un unico registro:
        {hop1, hop2, hop3}

    Pistas:
      - OPTIONAL MATCH (me)<-[:FOLLOWS*1..1]-(h1:User) — los que te siguen
        directamente.
      - count(DISTINCT h1) y luego encadena con WITH para hop2 y hop3.
      - hop2 incluye a hop1 (la formula es acumulativa por la naturaleza
        del traversal variable).
    Compruebalo:
      - Tiene que cumplirse hop1 <= hop2 <= hop3 siempre: son acumulativos.
        Si en algun usuario baja, estas contando solo los de ese salto
        exacto en vez del alcance acumulado.
      - hop1 tiene que coincidir con los followers de ese usuario en el
        ejercicio basico 2.
      - Ninguno puede superar el total de usuarios del grafo.
    """
    return exercise_placeholder("Neo4j-advanced-3",
        "Tres OPTIONAL MATCH con FOLLOWS*1..k entrante, k=1,2,3")


@router.get("/famous-distances")
async def neo4j_famous_distances(user_id: str):
    """
    EJERCICIO Neo4j-advanced-4: Distancia desde famosos a ti.

    Para una lista cableada de usernames famosos, calcula la distancia
    minima de FOLLOWS desde cada famoso hasta `user_id` (entrante:
    famous → me). Si no hay camino, distancia = -1.

    Devuelve un registro por famoso:
        {username, display_name, followers, distance}
    ordenado por distance ascendente.

    Pistas:
      - UNWIND $names AS fname para iterar sobre la lista.
      - shortestPath((famous)-[:FOLLOWS*..6]->(me)) — esta vez con
        direccion (entrante a me).
      - CASE WHEN p IS NULL THEN -1 ELSE length(p) END.
    Compruebalo:
      - Los que no tienen camino salen con -1, y al ordenar ascendente se
        te iran arriba del todo: comprueba que no los estas mezclando con
        los de distancia real.
      - Ninguna distancia puede pasar de 6, que es el limite del patron.
      - Aqui la direccion SI importa (famoso -> tu). Si te sale la misma
        distancia que en sentido contrario para todos, la has perdido.
    """
    famous_usernames = [
        "elonmusk", "taylorswift", "leomessi", "ibaboreal",
        "rosalia", "auronplay", "shakira", "jbalvin",
    ]
    return exercise_placeholder("Neo4j-advanced-4",
        "UNWIND + shortestPath dirigido + CASE WHEN p IS NULL")

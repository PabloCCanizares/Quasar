# Ejercicios Neo4j

Los ejercicios de Cypher estan en estos archivos:

- `neo4j_basic_ex.py`
- `neo4j_intermediate_ex.py`
- `neo4j_advanced_ex.py`

Mientras `LAB_NEO4J` este vacio, la app usa estos archivos `_ex.py`.

Cuando termines de implementar un ejercicio, reinicia el contenedor de la app
para que FastAPI vuelva a cargar el codigo:

```bash
docker compose restart app
```

Despues recarga la pestaña **Neo4j** en la web.

Nota: no uses `./lab.sh unlock neo4j ...` salvo que seas profesor y quieras
mostrar las soluciones oficiales.

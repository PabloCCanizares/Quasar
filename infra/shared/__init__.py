"""Quasar — librerías compartidas entre apps.

Cada app importa de `infra.shared.*` lo que necesite:
  - `config_base`: lectura de variables de entorno + defaults estándar.
  - `mongo`:       clientes async/sync para MongoDB.
  - `neo4j`:       driver y helpers para Neo4j.
  - `spark`:       constructor de SparkSession.

Las apps añaden encima de esto su configuración específica (paths del data lake,
flags propios, etc.).
"""

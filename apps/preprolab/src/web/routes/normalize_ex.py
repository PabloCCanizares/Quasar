"""Bloque NORMALIZE — scaffolds (versión alumno).

Cinco ejercicios sobre las técnicas de escalado/normalización del Tema 5:

  NORM-1  zscore       x' = (x - μ) / σ
  NORM-2  minmax       x' = (x - min) / (max - min)  → [0, 1]
  NORM-3  robust       x' = (x - mediana) / IQR
  NORM-4  decimal      x' = x / 10^j
  NORM-5  compare      aplica los 4 y compara distribuciones + sensibilidad
                       a outliers

Flujo:
  1. Implementa las funciones aquí.
  2. ./lab.sh preprolab restart
  3. Recarga la pestaña Normalización.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.web.data_loader import TABLES, load_table

router = APIRouter(prefix="/api/preprolab/normalize", tags=["preprolab-normalize"])


def _exercise_placeholder(exercise: str, hint: str) -> dict:
    return {
        "error": "scaffold",
        "exercise": exercise,
        "hint": hint,
        "available": False,
    }


@router.get("/zscore/{tabla}/{columna}")
async def zscore(tabla: str, columna: str) -> dict:
    """
    EJERCICIO NORM-1 — Estandarización Z-score.

    Calcula x' = (x - μ) / σ. Resultado: media ≈ 0, std ≈ 1.

    Estructura esperada:
        {
          "table", "column", "method": "zscore",
          "parameters": {"mean", "std"},
          "stats_before", "stats_after",  # count, mean, median, std, min, max, q1, q3
          "histogram_before", "histogram_after",
          "outlier_sensitivity_note"  # texto explicativo
        }

    Pistas:
      - Si std=0, devolver warning.
      - histogram = numpy.histogram(clean, bins=30).

    Compruebalo:
      - La media del resultado tiene que quedar practicamente en 0 y la
        desviacion tipica en 1. Si no, no estas restando la media o no
        estas dividiendo por la desviacion.
      - El orden de los valores no cambia: el mayor sigue siendo el mayor.
      - Z-score no acota el rango, asi que es normal ver valores por encima
        de 3 si hay outliers.
    """
    return _exercise_placeholder(
        "NORM-1",
        "Implementa Z-score: (x - mean) / std. Devuelve stats antes/después.",
    )


@router.get("/minmax/{tabla}/{columna}")
async def minmax(tabla: str, columna: str) -> dict:
    """
    EJERCICIO NORM-2 — Min-Max scaling a [0, 1].

    x' = (x - min) / (max - min)

    Conserva proporción pero MUY sensible a outliers. Si hay un valor
    extremo, comprime el resto cerca de 0 (ejemplo PDF:
    [10,20,30,40,1000] → [0, 0.01, 0.02, 0.03, 1.0]).

    Estructura esperada (igual que zscore más):
        "compression_diagnostic": {
          "pct_data_in_0_0.1": float,
          "interpretation": str
        }

    Pistas:
      - rng = max - min.
      - compression = porcentaje de filas con valor normalizado <= 0.1.
      - Si compression > 30% → outliers comprimiendo.

    Compruebalo:
      - El minimo tiene que quedar exactamente en 0 y el maximo en 1.
      - Con outliers presentes, casi todos los datos se apelotonan cerca del
        0. Eso NO es un fallo: es justo el problema que el ejercicio quiere
        ensenarte, y se ve mejor en la comparativa de NORM-5.
    """
    return _exercise_placeholder(
        "NORM-2",
        "Implementa Min-Max + diagnóstico de compresión por outliers.",
    )


@router.get("/robust/{tabla}/{columna}")
async def robust(tabla: str, columna: str) -> dict:
    """
    EJERCICIO NORM-3 — Robust scaling.

    x' = (x - mediana) / IQR

    Equivalente a sklearn.RobustScaler. Recomendado cuando hay outliers.

    Estructura esperada (igual que zscore más):
        "parameters": {"median", "q1", "q3", "iqr"}

    Pistas:
      - mediana = series.median().
      - IQR = q3 - q1 = series.quantile(0.75) - series.quantile(0.25).
      - Si IQR=0 → warning.

    Compruebalo:
      - La mediana del resultado tiene que quedar en 0.
      - Comparado con Min-Max sobre los mismos datos, aqui los valores
        centrales quedan mucho mas repartidos: esa es la ventaja de usar
        mediana e IQR en vez de min y max.
      - Si el IQR es 0 (columna casi constante) hay que tratarlo aparte, o
        saldran infinitos.
    """
    return _exercise_placeholder(
        "NORM-3",
        "Implementa Robust scaling: (x - mediana) / IQR. Más resistente a outliers.",
    )


@router.get("/decimal/{tabla}/{columna}")
async def decimal(tabla: str, columna: str) -> dict:
    """
    EJERCICIO NORM-4 — Decimal Scaling.

    x' = x / 10^j  donde j = menor entero tal que max(|x'|) < 1.

    Útil cuando los valores son grandes y mantienen proporción.

    Estructura esperada:
        "parameters": {"j", "divisor", "max_abs_original"}

    Pistas:
      - max_abs = series.abs().max().
      - j = int(np.ceil(np.log10(max_abs))) si max_abs >= 1, sino 0.
      - divisor = 10 ** j.

    Compruebalo:
      - Todos los valores tienen que quedar dentro de [-1, 1].
      - El divisor es una potencia de 10, asi que los digitos significativos
        no cambian: solo se mueve la coma. Comprueba que 84.2 se convierte en
        0.842 y no en otra cosa.
    """
    return _exercise_placeholder(
        "NORM-4",
        "Implementa Decimal Scaling: divide por 10^j donde j = ceil(log10(max|x|)).",
    )


@router.get("/compare/{tabla}/{columna}")
async def compare(tabla: str, columna: str) -> dict:
    """
    EJERCICIO NORM-5 — Comparativa de los 4 métodos.

    Aplica los 4 sobre la misma columna y devuelve estadísticos +
    histogramas + diagnóstico de compresión + interpretación.

    Estructura esperada:
        {
          "table", "column", "n", "original_stats",
          "methods": {
            "zscore":  {"params", "stats", "histogram", "compression_at_0_0.1"},
            "minmax":  ...,
            "robust":  ...,
            "decimal": ...
          },
          "interpretation": [str],  # observaciones automáticas
          "summary_table": [
            {"method", "min", "max", "std", "pct_in_0_0.1"}, ...
          ]
        }

    Pistas:
      - Reutiliza la lógica de NORM-1/2/3/4 internamente (o llámalos).
      - Interpretación útil: si pct_in_0_0.1 > 30 en minmax, hay outliers.
      - Si std_robust < 0.5 * std_zscore, también indica outliers.

    Compruebalo:
      - Los cuatro metodos tienen que conservar el orden de los datos: el
        robot mas caliente sigue siendo el mas caliente en los cuatro.
      - Mira que porcentaje de datos queda en el primer 10% del rango con
        cada metodo. Con outliers, Min-Max y Decimal apelotonan casi todo
        ahi, y Robust no. Ese contraste es el resultado que se busca.
      - Si los cuatro te dan distribuciones parecidas, comprueba que estas
        usando una columna que de verdad tenga outliers.
    """
    return _exercise_placeholder(
        "NORM-5",
        "Aplica los 4 métodos y devuelve summary_table + diagnósticos "
        "de sensibilidad a outliers (Min-Max compression > 30%, etc.).",
    )

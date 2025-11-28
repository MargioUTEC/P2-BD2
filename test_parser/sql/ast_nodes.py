# test_parser/sql/ast_nodes.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Union


# ============================================================
# Tipos de condición
# ============================================================

@dataclass
class ConditionNode:
    """
    Condición simple del tipo:
        atributo OPERADOR valor

    Ejemplos:
        artist = "Radiohead"
        year >= 2010
        genre != "Pop"
    """
    attribute: str      # nombre de la columna (artist, year, genre, track_id, ...)
    operator: str       # "=", "!=", "<", "<=", ">", ">="
    value: Any          # valor a comparar (str, int, float, ...)

    def __repr__(self) -> str:
        return f"{self.attribute} {self.operator} {self.value!r}"


@dataclass
class BetweenConditionNode:
    """
    Condición de rango:
        atributo BETWEEN valor1 AND valor2

    Ejemplo:
        year BETWEEN 2010 AND 2020
    """
    attribute: str
    value1: Any
    value2: Any

    def __repr__(self) -> str:
        return f"{self.attribute} BETWEEN {self.value1!r} AND {self.value2!r}"


@dataclass
class ConditionComplexNode:
    """
    Condición compuesta con operadores lógicos AND / OR.

    Ejemplos:
        artist = "Radiohead" AND year >= 2000
        (genre = "Electronic" OR genre = "Techno") AND year >= 2015
    """
    left: ConditionType
    operator: str   # "AND" o "OR"
    right: ConditionType

    def __repr__(self) -> str:
        return f"({self.left} {self.operator} {self.right})"


# Tipo recursivo para anotaciones
ConditionType = Union[ConditionNode, BetweenConditionNode, ConditionComplexNode]


# ============================================================
# Nodo principal de consulta: SELECT ... FROM ... WHERE ...
# ============================================================

@dataclass
class SelectWhereNode:
    """
    Representa una sentencia SELECT con posible cláusula WHERE.

    Ejemplos:

        SELECT * FROM metadata WHERE artist = "Radiohead";

        SELECT track_id, title, artist
        FROM metadata
        WHERE genre = "Rock" AND year BETWEEN 2000 AND 2010;
    """
    table_name: Optional[str]          # normalmente "metadata"
    columns: List[str]                 # ["*"] o lista de columnas específicas
    condition: Optional[ConditionType] # árbol de condiciones o None si no hay WHERE
    using_index: Optional[str] = None  # opcional; por ahora se puede ignorar

    def __repr__(self) -> str:
        cols = ", ".join(self.columns) if self.columns else "*"
        table = self.table_name or "<no-table>"
        where = f" WHERE {self.condition}" if self.condition is not None else ""
        using = f" USING {self.using_index}" if self.using_index else ""
        return f"<SELECT {cols} FROM {table}{using}{where}>"



__all__ = [
    "ConditionNode",
    "BetweenConditionNode",
    "ConditionComplexNode",
    "ConditionType",
    "SelectWhereNode",
]

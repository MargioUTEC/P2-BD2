# audio/sql/metadata_query_engine.py

from __future__ import annotations
from lark import Tree
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from audio.config_metadata import SQLITE_DB_PATH

from .ast_nodes import (
    ConditionNode,
    BetweenConditionNode,
    ConditionComplexNode,
    ConditionType,
    SelectWhereNode,
)
from .parser_sql import ParserSQL


# ============================================================
# Utilidades internas
# ============================================================

ALLOWED_TABLES = {"metadata"}
ALLOWED_COLUMNS = {"track_id", "title", "artist", "genre", "year"}


def normalize_tid(value: Any) -> str:
    """
    Normaliza un track_id a 6 dígitos, solo si luce como número.
    Ejemplos:
        34996   -> "034996"
        "34996" -> "034996"
        "034996"-> "034996"
    """
    s = str(value).strip()
    if s.isdigit():
        return s.zfill(6)
    return s


# ============================================================
# MetadataQueryEngine
# ============================================================

class MetadataQueryEngine:
    """
    Motor de consultas para la tabla metadata (metadata.db).

    Soporta:
      - SELECT ... FROM metadata WHERE ...
      - Entrada corta: solo la condición WHERE
        (ej: 'artist = "Radiohead" AND year >= 2000')

    Uso típico:

        engine = MetadataQueryEngine()
        result = engine.run_query('artist = "Radiohead" AND year >= 2000')

        # o:
        result = engine.run_query(
            'SELECT track_id, title FROM metadata WHERE genre = "Rock";'
        )

    El resultado es un dict:

        {
            "sql": "SELECT * FROM metadata WHERE artist = ? AND year >= ?;",
            "params": ["Radiohead", 2000],
            "rows": [ { "track_id": "...", "title": "...", ... }, ... ]
        }
    """

    def __init__(self, db_path: Union[str, Path, None] = None) -> None:
        if db_path is None:
            db_path = SQLITE_DB_PATH

        self.db_path = Path(db_path)
        self.parser = ParserSQL()

    # -----------------------------
    # API pública
    # -----------------------------

    def run_query(self, user_text: str) -> Dict[str, Any]:
        """
        Ejecuta una consulta de usuario sobre metadata.db.

        - Si user_text comienza con SELECT:
            se interpreta como SQL completo.
        - Si no, se asume que es solo la condición WHERE y se envuelve en:
            SELECT * FROM metadata WHERE {user_text}

        Devuelve dict con:
            - "sql": str   (consulta ejecutada)
            - "params": list
            - "rows": list[dict]
        """
        query_text = user_text.strip()

        # Forma corta: solo condición
        if not query_text.lower().startswith("select"):
            query_text = f"SELECT * FROM metadata WHERE {query_text}"

        ast = self.parser.parse(query_text)

        # La gramática podría devolver lista de sentencias; nos quedamos con la primera
        if isinstance(ast, list):
            if not ast:
                raise ValueError("La consulta no contiene sentencias válidas.")
            stmt = ast[0]
        else:
            stmt = ast

        if not isinstance(stmt, SelectWhereNode):
            raise ValueError("Solo se soportan sentencias SELECT para metadata.")

        # Traducción AST → SQL + params
        sql, params = self._build_sql(stmt)

        # Ejecución en SQLite
        rows = self._execute_sql(sql, params)

        return {
            "sql": sql,
            "params": params,
            "rows": rows,
        }

    # -----------------------------
    # Construcción de SQL
    # -----------------------------

    def _build_sql(self, stmt: SelectWhereNode) -> Tuple[str, List[Any]]:
        # Tabla: por defecto "metadata"
        table = (stmt.table_name or "metadata").lower()
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Tabla no permitida: {table!r}. Solo se admite 'metadata'.")

        # Columnas
        columns = stmt.columns or ["*"]
        if columns == ["*"]:
            cols_sql = "*"
        else:
            # Validar cada columna
            safe_cols = []
            for col in columns:
                col_name = str(col).strip()
                if col_name not in ALLOWED_COLUMNS:
                    raise ValueError(f"Columna no permitida: {col_name!r}")
                safe_cols.append(col_name)
            cols_sql = ", ".join(safe_cols)

        # WHERE
        where_sql = ""
        params: List[Any] = []
        if stmt.condition is not None:
            where_sql, params = self._build_where(stmt.condition)
            if where_sql:
                where_sql = " WHERE " + where_sql

        sql = f"SELECT {cols_sql} FROM {table}{where_sql};"
        return sql, params

    def _build_where(self, cond: Any) -> Tuple[str, List[Any]]:
        """
        Convierte un árbol de condiciones (o incluso un Tree crudo de Lark)
        en (sql_fragment, params).

        Soporta:
          - ConditionNode
          - BetweenConditionNode
          - ConditionComplexNode
          - Tree('and_condition_chain', [...])
          - Tree('or_condition_chain', [...])
          - Tree con un solo hijo (se delega en él)
        """

        # ---------------------------------------------
        # 1) Caso especial: la gramática dejó un Tree
        # ---------------------------------------------
        if isinstance(cond, Tree):
            # Si solo envuelve otra condición, delegamos directamente
            if len(cond.children) == 1:
                return self._build_where(cond.children[0])

            # and_condition_chain:  (left AND right)
            if cond.data == "and_condition_chain":
                if len(cond.children) != 2:
                    raise ValueError(
                        f"and_condition_chain inesperado con {len(cond.children)} hijos"
                    )
                left, right = cond.children
                node = ConditionComplexNode(
                    left=left,
                    operator="AND",
                    right=right,
                )
                return self._build_where(node)

            # or_condition_chain:  (left OR right)
            if cond.data == "or_condition_chain":
                if len(cond.children) != 2:
                    raise ValueError(
                        f"or_condition_chain inesperado con {len(cond.children)} hijos"
                    )
                left, right = cond.children
                node = ConditionComplexNode(
                    left=left,
                    operator="OR",
                    right=right,
                )
                return self._build_where(node)

            # Cualquier otro Tree no esperado
            raise TypeError(f"Tree de condición no soportado: {cond.data!r}")

        # ---------------------------------------------
        # 2) Condición simple: atributo OP valor
        # ---------------------------------------------
        if isinstance(cond, ConditionNode):
            col = cond.attribute.strip()
            op = cond.operator.strip()

            if col not in ALLOWED_COLUMNS:
                raise ValueError(f"Columna no permitida en condición: {col!r}")

            value = cond.value
            if col == "track_id":
                value = normalize_tid(value)

            fragment = f"{col} {op} ?"
            return fragment, [value]

        # ---------------------------------------------
        # 3) BETWEEN
        # ---------------------------------------------
        if isinstance(cond, BetweenConditionNode):
            col = cond.attribute.strip()
            if col not in ALLOWED_COLUMNS:
                raise ValueError(f"Columna no permitida en condición BETWEEN: {col!r}")

            v1, v2 = cond.value1, cond.value2
            if col == "track_id":
                v1 = normalize_tid(v1)
                v2 = normalize_tid(v2)

            fragment = f"{col} BETWEEN ? AND ?"
            return fragment, [v1, v2]

        # ---------------------------------------------
        # 4) Condición compuesta AND / OR
        # ---------------------------------------------
        if isinstance(cond, ConditionComplexNode):
            left_sql, left_params = self._build_where(cond.left)
            right_sql, right_params = self._build_where(cond.right)

            op = cond.operator.strip().upper()
            if op not in {"AND", "OR"}:
                raise ValueError(f"Operador lógico no soportado: {op!r}")

            fragment = f"({left_sql} {op} {right_sql})"
            return fragment, left_params + right_params

        # ---------------------------------------------
        # 5) Cualquier otra cosa es inesperada
        # ---------------------------------------------
        raise TypeError(f"Tipo de condición no soportado: {type(cond)}")

    # -----------------------------
    # Ejecución SQLite
    # -----------------------------

    def _execute_sql(self, sql: str, params: List[Any]) -> List[Dict[str, Any]]:
        if not self.db_path.exists():
            raise FileNotFoundError(f"No se encontró la base de datos: {self.db_path}")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]

        return rows


__all__ = ["MetadataQueryEngine"]

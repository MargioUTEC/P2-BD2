# audio/sql/parser_sql.py

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Union

from lark import Lark, Transformer, Token, Tree

from .ast_nodes import (
    ConditionNode,
    BetweenConditionNode,
    ConditionComplexNode,
    ConditionType,
    SelectWhereNode,
)


# ============================================================
# Helpers internos
# ============================================================

def _tokval(x: Any) -> Any:
    """Devuelve el valor crudo de un Token o el propio objeto."""
    if isinstance(x, Token):
        return x.value
    return x


def _strip_quotes(s: str) -> str:
    """Elimina comillas dobles de una cadena tipo \"texto\"."""
    if isinstance(s, str) and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


# ============================================================
# Transformer: Árbol de Lark → AST propio
# ============================================================

class SQLTransformer(Transformer):
    """
    Transforma el árbol de Lark (según grammar_sql.lark) en nuestros nodos AST.

    Nos interesan principalmente:
      - select_stmt
      - where_clause
      - condition_*
      - column_list
      - value
    """

    # ---------- WHERE ----------

    def where_clause(self, children: List[Any]) -> ConditionType:
        # Regla simple: WHERE <condición>
        return children[0]

    # ---------- SELECT ----------

    def select_stmt(self, children: List[Any]) -> SelectWhereNode:
        """
        children típicamente:
          [column_list, table_name, (opcional using_clause), (opcional where_clause)]

        La gramática original soporta USING; aquí lo dejamos por si acaso,
        pero en nuestro proyecto de metadata no obligamos a usarlo.
        """
        columns = children[0]
        table = str(_tokval(children[1]))

        using_index = None
        condition: ConditionType | None = None

        for c in children[2:]:
            # En la gramática original, USING se transformaba en una lista de nombres
            if isinstance(c, list) and c:
                # ['ISAM'] o ['AVL'], etc.
                using_index = str(c[0]).upper()
            else:
                # asume que es la condición WHERE
                condition = c

        return SelectWhereNode(
            table_name=table,
            columns=columns,
            condition=condition,
            using_index=using_index,
        )

    # ---------- Columnas ----------

    def column_list(self, children: List[Any]) -> List[str]:
        """
        Maneja:
          *              → ["*"]
          col1, col2,... → ["col1", "col2", ...]
        """
        if len(children) == 1 and isinstance(children[0], Token) and children[0].value == "*":
            return ["*"]
        return [str(_tokval(c)) for c in children]

    # ---------- Valores ----------

    def value(self, children: List[Any]) -> Any:
        """
        Convierte un token de valor en Python:
          - "texto" → str
          - 123     → int
          - 3.14    → float
        """
        if not children:
            return None

        v = children[0]

        if isinstance(v, Token):
            # Strings con comillas escapadas
            if v.type == "ESCAPED_STRING":
                return _strip_quotes(v.value)

            txt = v.value

            # Intentar int
            try:
                return int(txt)
            except ValueError:
                pass

            # Intentar float
            try:
                return float(txt)
            except ValueError:
                pass

            # Si no es numérico, devolver como string cruda
            return txt

        # Si ya es algo transformado (por ejemplo, otro tipo)
        return v

    # ---------- Condiciones simples ----------

    def condition_comparison(self, children: List[Any]) -> ConditionNode:
        """
        Regla del tipo:
          columna op valor
        ej:
          artist = "Radiohead"
          year >= 2010
        """
        col, op, val = children
        return ConditionNode(
            attribute=str(_tokval(col)),
            operator=str(_tokval(op)),
            value=val,
        )

    def condition_between(self, children: List[Any]) -> BetweenConditionNode:
        """
        Regla del tipo:
          columna BETWEEN v1 AND v2
        """
        col, v1, v2 = children
        return BetweenConditionNode(
            attribute=str(_tokval(col)),
            value1=v1,
            value2=v2,
        )

    # ---------- Condiciones compuestas ----------

    def condition_complex(self, children: List[Any]) -> ConditionType:
        """
        children = [cond1, 'AND', cond2, 'OR', cond3, ...]
        Se convierte en un árbol binario encadenado de ConditionComplexNode.
        """
        if len(children) < 3:
            # Solo una condición
            return children[0]

        # Primer par: cond1 OP cond2
        node: ConditionType = ConditionComplexNode(
            left=children[0],
            operator=str(_tokval(children[1])).upper(),
            right=children[2],
        )

        # Encadenar el resto (si existe)
        i = 3
        while i + 1 < len(children):
            op = str(_tokval(children[i])).upper()
            right = children[i + 1]
            node = ConditionComplexNode(
                left=node,
                operator=op,
                right=right,
            )
            i += 2

        return node

    def grouped_condition(self, children: List[Any]) -> ConditionType:
        """
        Maneja condiciones entre paréntesis: ( ... )
        """
        return children[0]


# ============================================================
# Clase de alto nivel: ParserSQL
# ============================================================

class ParserSQL:
    """
    Envoltorio sencillo alrededor de Lark.

    Uso esperado:
        parser = ParserSQL()
        ast = parser.parse('SELECT * FROM metadata WHERE artist = "Radiohead";')
    """

    def __init__(self, grammar_path: str | None = None) -> None:
        if grammar_path is None:
            # Por defecto, buscar grammar_sql.lark en el mismo directorio que este archivo
            grammar_path = str(Path(__file__).with_name("grammar_sql.lark"))

        with open(grammar_path, "r", encoding="utf-8") as f:
            grammar = f.read()

        # No establecemos transformer aquí; lo aplicamos manualmente en parse()
        self.parser = Lark(
            grammar,
            start="start",
            parser="lalr",
        )

    def parse(self, query: str) -> Union[SelectWhereNode, list[SelectWhereNode], Any]:
        """
        Recibe una consulta SQL en texto y devuelve el AST transformado.

        Dependiendo de la gramática, el resultado puede ser:
          - Un solo SelectWhereNode
          - Una lista de nodos (si se permiten múltiples sentencias separadas por ;)
        """
        tree = self.parser.parse(query)
        transformer = SQLTransformer()
        return transformer.transform(tree)


__all__ = [
    "ParserSQL",
    "SQLTransformer",
]

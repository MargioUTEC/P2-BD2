"""
metadata_index_bptree.py
------------------------

Índice B+ Tree optimizado para almacenar metadata del dataset FMA.

Características clave:
- Todas las claves aparecen solo en hojas.
- Hojas enlazadas para búsquedas por rango eficientes.
- Inserción ordenada con splits automáticos.
- Escalable a > 100k registros.
- Permite búsquedas exactas y por rango rápidas.

Clave del índice: track_id   (int)
Valor: metadata unificada {track, genre, features, echonest, raw_*}
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


# ============================================================
# NODO DEL B+ TREE
# ============================================================

class BPlusTreeNode:
    def __init__(self, is_leaf: bool, order: int):
        self.is_leaf = is_leaf
        self.order = order

        self.keys: List[int] = []

        # Para nodos hoja
        self.values: Optional[List[Dict]] = [] if is_leaf else None

        # Para nodos internos
        self.children: Optional[List[BPlusTreeNode]] = [] if not is_leaf else None

        # Enlace entre hojas (para range queries)
        self.next: Optional[BPlusTreeNode] = None


# ============================================================
# B+ TREE COMPLETO
# ============================================================

class MetadataBPlusTree:
    def __init__(self, order: int = 32):
        self.order = order
        self.root = BPlusTreeNode(is_leaf=True, order=order)

    # --------------------------------------------------------
    # BÚSQUEDA EXACTA
    # --------------------------------------------------------
    def search(self, key: int) -> Optional[Dict]:
        node = self.root

        while not node.is_leaf:
            idx = self._find_position(node.keys, key)
            node = node.children[idx]

        # Buscar en la hoja exacta
        for i, k in enumerate(node.keys):
            if k == key:
                return node.values[i]

        return None

    # --------------------------------------------------------
    # BÚSQUEDA POR RANGO
    # --------------------------------------------------------
    def range_search(self, low: int, high: int) -> List[Dict]:
        node = self.root

        # Buscar hoja donde debería estar 'low'
        while not node.is_leaf:
            idx = self._find_position(node.keys, low)
            node = node.children[idx]

        result = []

        # Recorrer hojas enlazadas
        while node:
            for k, v in zip(node.keys, node.values):
                if low <= k <= high:
                    result.append(v)
                elif k > high:
                    return result
            node = node.next

        return result

    # --------------------------------------------------------
    # INSERCIÓN PRINCIPAL
    # --------------------------------------------------------
    def insert(self, key: int, value: Dict):
        root = self.root

        # Si raíz llena → dividir antes de insertar
        if len(root.keys) == self.order:
            new_root = BPlusTreeNode(is_leaf=False, order=self.order)
            new_root.children.append(root)
            self._split_child(new_root, 0)
            self.root = new_root

        self._insert_nonfull(self.root, key, value)

    # ============================================================
    # MÉTODOS AUXILIARES
    # ============================================================

    def _find_position(self, arr: List[int], key: int) -> int:
        """Retorna la posición donde key debe insertarse (binary-ish search)."""
        for i, existing_key in enumerate(arr):
            if key < existing_key:
                return i
        return len(arr)

    def _insert_nonfull(self, node: BPlusTreeNode, key: int, value: Dict):
        if node.is_leaf:

            # Evitar duplicados
            if key in node.keys:
                return

            idx = self._find_position(node.keys, key)
            node.keys.insert(idx, key)
            node.values.insert(idx, value)

        else:
            idx = self._find_position(node.keys, key)
            child = node.children[idx]

            # Si el hijo está lleno → dividir
            if len(child.keys) == self.order:
                self._split_child(node, idx)

                # Decidir a qué hijo ir después del split
                if key > node.keys[idx]:
                    child = node.children[idx + 1]

            self._insert_nonfull(child, key, value)

    # --------------------------------------------------------
    # SPLIT DE NODOS
    # --------------------------------------------------------
    def _split_child(self, parent: BPlusTreeNode, index: int):
        node = parent.children[index]
        mid = self.order // 2

        if node.is_leaf:
            # --- split de hoja ---
            new_leaf = BPlusTreeNode(is_leaf=True, order=self.order)

            # Movimiento de claves y valores
            new_leaf.keys = node.keys[mid:]
            new_leaf.values = node.values[mid:]

            node.keys = node.keys[:mid]
            node.values = node.values[:mid]

            # Enlazar hojas
            new_leaf.next = node.next
            node.next = new_leaf

            # Insertar clave promovida (primera del nuevo nodo)
            parent.keys.insert(index, new_leaf.keys[0])
            parent.children.insert(index + 1, new_leaf)

        else:
            # --- split interno ---
            new_internal = BPlusTreeNode(is_leaf=False, order=self.order)

            promote_key = node.keys[mid]

            new_internal.keys = node.keys[mid + 1:]
            new_internal.children = node.children[mid + 1:]

            node.keys = node.keys[:mid]
            node.children = node.children[:mid + 1]

            parent.keys.insert(index, promote_key)
            parent.children.insert(index + 1, new_internal)

# ============================================================
# CONSTRUCTOR DEL ÍNDICE
# ============================================================

def build_metadata_bptree(
    metadata_dict: Dict[str, Dict] = None,
    track_metadata: Dict[str, Dict] = None,
    order: int = 32
) -> MetadataBPlusTree:
    """
    Construye un B+Tree con todos los track_id de la metadata.

    Parámetros:
    - metadata_dict o track_metadata: diccionario {track_id: metadata}
    - order: grado del árbol

    Retorna:
    - MetadataBPlusTree completamente construido
    """

    # Acepta ambos nombres, el test usa track_metadata
    if metadata_dict is None and track_metadata is None:
        raise ValueError("Debes pasar metadata_dict= o track_metadata=")

    if metadata_dict is None:
        metadata_dict = track_metadata

    tree = MetadataBPlusTree(order)

    # Insertamos todos los track_id
    for tid, value in metadata_dict.items():
        try:
            tree.insert(int(tid), value)
        except Exception as e:
            print(f"[WARN] No se pudo insertar track_id={tid}: {e}")

    return tree

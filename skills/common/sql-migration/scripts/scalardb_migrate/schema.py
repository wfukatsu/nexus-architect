"""Lightweight table metadata used for access-path analysis (GET / partition SCAN / index SCAN / cross-partition SCAN).

The registry is populated from CREATE TABLE / CREATE INDEX statements found in the script, and/or from a
ScalarDB Schema Loader JSON file (https://scalardb.scalar-labs.com/docs/latest/schema-loader/).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class TableMeta:
    namespace: str | None
    name: str
    partition_key: list[str]
    clustering_key: list[str]
    clustering_order: dict[str, str]  # column -> ASC/DESC
    columns: dict[str, str]  # column -> ScalarDB type
    secondary_indexes: list[str] = field(default_factory=list)

    @property
    def primary_key(self) -> list[str]:
        return self.partition_key + self.clustering_key

    def qualified(self) -> str:
        return f"{self.namespace}.{self.name}" if self.namespace else self.name

    def to_schema_loader(self) -> dict:
        d = {
            "transaction": True,
            "partition-key": list(self.partition_key),
            "clustering-key": [f"{c} {self.clustering_order.get(c, 'ASC')}" for c in self.clustering_key],
            "columns": dict(self.columns),
        }
        if self.secondary_indexes:
            d["secondary-index"] = list(self.secondary_indexes)
        return d


class SchemaRegistry:
    def __init__(self) -> None:
        self._tables: dict[str, TableMeta] = {}

    def add(self, meta: TableMeta) -> None:
        self._tables[meta.name.lower()] = meta

    def get(self, name: str) -> TableMeta | None:
        return self._tables.get(name.lower())

    def add_index(self, table: str, column: str) -> None:
        meta = self.get(table)
        if meta and column not in meta.secondary_indexes:
            meta.secondary_indexes.append(column)

    def tables(self) -> list[TableMeta]:
        return list(self._tables.values())

    def to_schema_loader_json(self) -> str:
        return json.dumps({t.qualified(): t.to_schema_loader() for t in self.tables()}, indent=2)

    @classmethod
    def from_schema_loader_json(cls, path: str) -> "SchemaRegistry":
        reg = cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for qualified, spec in data.items():
            ns, _, name = qualified.rpartition(".")
            ck, order = [], {}
            for item in spec.get("clustering-key", []):
                col, _, o = item.partition(" ")
                ck.append(col)
                order[col] = (o or "ASC").upper()
            reg.add(TableMeta(ns or None, name, list(spec.get("partition-key", [])), ck, order,
                              dict(spec.get("columns", {})), list(spec.get("secondary-index", []))))
        return reg

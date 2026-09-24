from __future__ import annotations

import logging
from abc import ABC
from typing import Any, Iterable, Sequence

from core.connection import source_connection, target_connection


class BaseExtractor(ABC):
    SCHEMA: str = "itsm"
    TABLE: str = ""
    PRIMARY_KEY: str = ""
    COLUMNS: Sequence[str] = ()

    IMMUTABLE_ON_UPDATE: Sequence[str] = ("dt_inclusao",)

    IDENTITY_INSERT: bool = True

    BATCH_SIZE: int = 1000

    def __init__(self) -> None:
        if not self.TABLE or not self.PRIMARY_KEY or not self.COLUMNS:
            raise TypeError(
                f"{type(self).__name__} deve declarar TABLE, PRIMARY_KEY e COLUMNS."
            )
        if self.PRIMARY_KEY not in self.COLUMNS:
            raise TypeError(
                f"{type(self).__name__}: PRIMARY_KEY '{self.PRIMARY_KEY}' "
                f"não está em COLUMNS."
            )

    @property
    def full_table(self) -> str:
        return f"{self.SCHEMA}.{self.TABLE}"

    @property
    def update_columns(self) -> list[str]:
        excluded = {self.PRIMARY_KEY, *self.IMMUTABLE_ON_UPDATE}
        return [c for c in self.COLUMNS if c not in excluded]

    def run(self) -> int:
        logging.info("EL: %s — iniciando", self.full_table)

        rows = self.extract()
        logging.info("Extraídas %d linhas de %s", len(rows), self.full_table)
        if not rows:
            logging.info("EL: %s — nada a carregar", self.full_table)
            return 0

        rows = list(self.transform(rows))
        if not rows:
            logging.info("EL: %s — transform() descartou todas as linhas", self.full_table)
            return 0

        loaded = self.load(rows)
        logging.info("Carregadas %d linhas em %s", loaded, self.full_table)
        return loaded

    def build_select_sql(self) -> str:
        return f"SELECT {', '.join(self.COLUMNS)} FROM {self.full_table}"

    def extract(self) -> list[tuple]:
        with source_connection() as src:
            cursor = src.cursor()
            cursor.execute(self.build_select_sql())
            return [tuple(row) for row in cursor.fetchall()]

    def transform(self, rows: list[tuple]) -> Iterable[tuple]:
        return rows

    def build_merge_sql(self) -> str:
        cols = list(self.COLUMNS)
        placeholders = ",".join("?" * len(cols))
        col_list = ", ".join(cols)
        source_alias = ", ".join(cols)
        set_clause = ",\n                ".join(
            f"{c} = s.{c}" for c in self.update_columns
        )
        insert_values = ", ".join(f"s.{c}" for c in cols)

        return f"""
        MERGE {self.full_table} AS t
        USING (VALUES ({placeholders})) AS s({source_alias})
        ON t.{self.PRIMARY_KEY} = s.{self.PRIMARY_KEY}
        WHEN MATCHED THEN
            UPDATE SET
                {set_clause}
        WHEN NOT MATCHED THEN
            INSERT ({col_list})
            VALUES ({insert_values});
        """

    def before_load(self, cursor: Any) -> None:
        return None

    def after_load(self, cursor: Any) -> None:
        return None

    def load(self, rows: list[tuple]) -> int:
        merge_sql = self.build_merge_sql()
        try:
            with target_connection() as dst:
                cursor = dst.cursor()
                if self.IDENTITY_INSERT:
                    cursor.execute(f"SET IDENTITY_INSERT {self.full_table} ON")

                self.before_load(cursor)

                for start in range(0, len(rows), self.BATCH_SIZE):
                    cursor.executemany(merge_sql, rows[start:start + self.BATCH_SIZE])

                self.after_load(cursor)

                if self.IDENTITY_INSERT:
                    cursor.execute(f"SET IDENTITY_INSERT {self.full_table} OFF")
                dst.commit()
            return len(rows)
        except Exception as exc:
            logging.error("Erro ao carregar %s: %s", self.full_table, exc)
            raise

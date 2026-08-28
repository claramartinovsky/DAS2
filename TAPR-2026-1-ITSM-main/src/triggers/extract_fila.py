import logging
import os
import pyodbc


def _get_conn(server, database, user, password):
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )


def run() -> None:
    logging.info('EL: itsm.fila')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute("SELECT id_fila, cd_fila, nm_fila, ds_descricao, fl_ativo, "
                    "dt_inclusao, dt_atualizacao, nm_sistema_origem, cd_registro_origem "
                    "FROM itsm.fila")
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.fila")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.fila AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?))
              AS s(id_fila, cd_fila, nm_fila, ds_descricao, fl_ativo,
                   dt_inclusao, dt_atualizacao, nm_sistema_origem, cd_registro_origem)
        ON t.id_fila = s.id_fila
        WHEN MATCHED THEN
            UPDATE SET
                cd_fila            = s.cd_fila,
                nm_fila            = s.nm_fila,
                ds_descricao       = s.ds_descricao,
                fl_ativo           = s.fl_ativo,
                dt_atualizacao     = s.dt_atualizacao,
                nm_sistema_origem  = s.nm_sistema_origem,
                cd_registro_origem = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_fila, cd_fila, nm_fila, ds_descricao, fl_ativo,
                    dt_inclusao, dt_atualizacao, nm_sistema_origem, cd_registro_origem)
            VALUES (s.id_fila, s.cd_fila, s.nm_fila, s.ds_descricao, s.fl_ativo,
                    s.dt_inclusao, s.dt_atualizacao, s.nm_sistema_origem,
                    s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.fila ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.fila OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.fila")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.fila: {str(e)}")
        raise

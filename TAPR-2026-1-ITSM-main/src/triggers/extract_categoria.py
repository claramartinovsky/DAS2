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
    logging.info('EL: itsm.categoria')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute("SELECT id_categoria, cd_categoria, nm_categoria, ds_descricao, "
                    "fl_ativo, dt_inclusao, dt_atualizacao, nm_sistema_origem, "
                    "cd_registro_origem FROM itsm.categoria")
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.categoria")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.categoria AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?))
              AS s(id_categoria, cd_categoria, nm_categoria, ds_descricao,
                   fl_ativo, dt_inclusao, dt_atualizacao, nm_sistema_origem,
                   cd_registro_origem)
        ON t.id_categoria = s.id_categoria
        WHEN MATCHED THEN
            UPDATE SET
                cd_categoria       = s.cd_categoria,
                nm_categoria       = s.nm_categoria,
                ds_descricao       = s.ds_descricao,
                fl_ativo           = s.fl_ativo,
                dt_atualizacao     = s.dt_atualizacao,
                nm_sistema_origem  = s.nm_sistema_origem,
                cd_registro_origem = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_categoria, cd_categoria, nm_categoria, ds_descricao,
                    fl_ativo, dt_inclusao, dt_atualizacao, nm_sistema_origem,
                    cd_registro_origem)
            VALUES (s.id_categoria, s.cd_categoria, s.nm_categoria, s.ds_descricao,
                    s.fl_ativo, s.dt_inclusao, s.dt_atualizacao, s.nm_sistema_origem,
                    s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.categoria ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.categoria OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.categoria")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.categoria: {str(e)}")
        raise

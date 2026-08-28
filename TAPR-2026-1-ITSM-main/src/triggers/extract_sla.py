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
    logging.info('EL: itsm.sla')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute("SELECT id_sla, cd_sla, nm_sla, qt_meta_minutos, ds_descricao, "
                    "fl_ativo, dt_inclusao, dt_atualizacao, nm_sistema_origem, "
                    "cd_registro_origem FROM itsm.sla")
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.sla")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.sla AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?,?))
              AS s(id_sla, cd_sla, nm_sla, qt_meta_minutos, ds_descricao,
                   fl_ativo, dt_inclusao, dt_atualizacao, nm_sistema_origem,
                   cd_registro_origem)
        ON t.id_sla = s.id_sla
        WHEN MATCHED THEN
            UPDATE SET
                cd_sla             = s.cd_sla,
                nm_sla             = s.nm_sla,
                qt_meta_minutos    = s.qt_meta_minutos,
                ds_descricao       = s.ds_descricao,
                fl_ativo           = s.fl_ativo,
                dt_atualizacao     = s.dt_atualizacao,
                nm_sistema_origem  = s.nm_sistema_origem,
                cd_registro_origem = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_sla, cd_sla, nm_sla, qt_meta_minutos, ds_descricao,
                    fl_ativo, dt_inclusao, dt_atualizacao, nm_sistema_origem,
                    cd_registro_origem)
            VALUES (s.id_sla, s.cd_sla, s.nm_sla, s.qt_meta_minutos, s.ds_descricao,
                    s.fl_ativo, s.dt_inclusao, s.dt_atualizacao, s.nm_sistema_origem,
                    s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.sla ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.sla OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.sla")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.sla: {str(e)}")
        raise

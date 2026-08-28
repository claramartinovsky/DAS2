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
    logging.info('EL: itsm.analista')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute("SELECT id_analista, cd_analista, nm_analista, ds_email, "
                    "ds_nivel, id_fila_atual, fl_ativo, dt_inclusao, dt_atualizacao, "
                    "nm_sistema_origem, cd_registro_origem FROM itsm.analista")
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.analista")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    # id_fila_atual é FK para itsm.fila — os ids batem pois fila é carregada
    # com IDENTITY_INSERT ON preservando os ids do banco de origem.
    merge_sql = """
        MERGE itsm.analista AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?,?,?))
              AS s(id_analista, cd_analista, nm_analista, ds_email, ds_nivel,
                   id_fila_atual, fl_ativo, dt_inclusao, dt_atualizacao,
                   nm_sistema_origem, cd_registro_origem)
        ON t.id_analista = s.id_analista
        WHEN MATCHED THEN
            UPDATE SET
                cd_analista        = s.cd_analista,
                nm_analista        = s.nm_analista,
                ds_email           = s.ds_email,
                ds_nivel           = s.ds_nivel,
                id_fila_atual      = s.id_fila_atual,
                fl_ativo           = s.fl_ativo,
                dt_atualizacao     = s.dt_atualizacao,
                nm_sistema_origem  = s.nm_sistema_origem,
                cd_registro_origem = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_analista, cd_analista, nm_analista, ds_email, ds_nivel,
                    id_fila_atual, fl_ativo, dt_inclusao, dt_atualizacao,
                    nm_sistema_origem, cd_registro_origem)
            VALUES (s.id_analista, s.cd_analista, s.nm_analista, s.ds_email,
                    s.ds_nivel, s.id_fila_atual, s.fl_ativo, s.dt_inclusao,
                    s.dt_atualizacao, s.nm_sistema_origem, s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.analista ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.analista OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.analista")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.analista: {str(e)}")
        raise

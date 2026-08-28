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
    logging.info('EL: itsm.csat_avaliacao')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute(
            "SELECT id_csat_avaliacao, id_chamado, id_analista, nr_score, "
            "ds_comentario, dt_avaliacao, dt_inclusao, dt_atualizacao, "
            "nm_sistema_origem, cd_registro_origem FROM itsm.csat_avaliacao"
        )
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.csat_avaliacao")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.csat_avaliacao AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?,?))
              AS s(id_csat_avaliacao, id_chamado, id_analista, nr_score,
                   ds_comentario, dt_avaliacao, dt_inclusao, dt_atualizacao,
                   nm_sistema_origem, cd_registro_origem)
        ON t.id_csat_avaliacao = s.id_csat_avaliacao
        WHEN MATCHED THEN
            UPDATE SET
                id_chamado         = s.id_chamado,
                id_analista        = s.id_analista,
                nr_score           = s.nr_score,
                ds_comentario      = s.ds_comentario,
                dt_avaliacao       = s.dt_avaliacao,
                dt_atualizacao     = s.dt_atualizacao,
                nm_sistema_origem  = s.nm_sistema_origem,
                cd_registro_origem = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_csat_avaliacao, id_chamado, id_analista, nr_score,
                    ds_comentario, dt_avaliacao, dt_inclusao, dt_atualizacao,
                    nm_sistema_origem, cd_registro_origem)
            VALUES (s.id_csat_avaliacao, s.id_chamado, s.id_analista, s.nr_score,
                    s.ds_comentario, s.dt_avaliacao, s.dt_inclusao, s.dt_atualizacao,
                    s.nm_sistema_origem, s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.csat_avaliacao ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.csat_avaliacao OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.csat_avaliacao")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.csat_avaliacao: {str(e)}")
        raise

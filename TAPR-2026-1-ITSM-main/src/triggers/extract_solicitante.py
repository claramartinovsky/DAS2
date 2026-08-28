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
    logging.info('EL: itsm.solicitante')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute("SELECT id_solicitante, cd_solicitante, id_cliente_organizacao, "
                    "nm_solicitante, ds_email, ds_telefone, fl_ativo, dt_inclusao, "
                    "dt_atualizacao, nm_sistema_origem, cd_registro_origem "
                    "FROM itsm.solicitante")
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.solicitante")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.solicitante AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?,?,?))
              AS s(id_solicitante, cd_solicitante, id_cliente_organizacao,
                   nm_solicitante, ds_email, ds_telefone, fl_ativo, dt_inclusao,
                   dt_atualizacao, nm_sistema_origem, cd_registro_origem)
        ON t.id_solicitante = s.id_solicitante
        WHEN MATCHED THEN
            UPDATE SET
                cd_solicitante         = s.cd_solicitante,
                id_cliente_organizacao = s.id_cliente_organizacao,
                nm_solicitante         = s.nm_solicitante,
                ds_email               = s.ds_email,
                ds_telefone            = s.ds_telefone,
                fl_ativo               = s.fl_ativo,
                dt_atualizacao         = s.dt_atualizacao,
                nm_sistema_origem      = s.nm_sistema_origem,
                cd_registro_origem     = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_solicitante, cd_solicitante, id_cliente_organizacao,
                    nm_solicitante, ds_email, ds_telefone, fl_ativo, dt_inclusao,
                    dt_atualizacao, nm_sistema_origem, cd_registro_origem)
            VALUES (s.id_solicitante, s.cd_solicitante, s.id_cliente_organizacao,
                    s.nm_solicitante, s.ds_email, s.ds_telefone, s.fl_ativo,
                    s.dt_inclusao, s.dt_atualizacao, s.nm_sistema_origem,
                    s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.solicitante ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.solicitante OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.solicitante")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.solicitante: {str(e)}")
        raise

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
    logging.info('EL: itsm.cliente_organizacao')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute("SELECT id_cliente_organizacao, cd_cliente_organizacao, "
                    "nm_cliente_organizacao, nr_cnpj, fl_ativo, dt_inclusao, "
                    "dt_atualizacao, nm_sistema_origem, cd_registro_origem "
                    "FROM itsm.cliente_organizacao")
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.cliente_organizacao")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.cliente_organizacao AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?))
              AS s(id_cliente_organizacao, cd_cliente_organizacao,
                   nm_cliente_organizacao, nr_cnpj, fl_ativo, dt_inclusao,
                   dt_atualizacao, nm_sistema_origem, cd_registro_origem)
        ON t.id_cliente_organizacao = s.id_cliente_organizacao
        WHEN MATCHED THEN
            UPDATE SET
                cd_cliente_organizacao = s.cd_cliente_organizacao,
                nm_cliente_organizacao = s.nm_cliente_organizacao,
                nr_cnpj                = s.nr_cnpj,
                fl_ativo               = s.fl_ativo,
                dt_atualizacao         = s.dt_atualizacao,
                nm_sistema_origem      = s.nm_sistema_origem,
                cd_registro_origem     = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_cliente_organizacao, cd_cliente_organizacao,
                    nm_cliente_organizacao, nr_cnpj, fl_ativo, dt_inclusao,
                    dt_atualizacao, nm_sistema_origem, cd_registro_origem)
            VALUES (s.id_cliente_organizacao, s.cd_cliente_organizacao,
                    s.nm_cliente_organizacao, s.nr_cnpj, s.fl_ativo, s.dt_inclusao,
                    s.dt_atualizacao, s.nm_sistema_origem, s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.cliente_organizacao ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.cliente_organizacao OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.cliente_organizacao")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.cliente_organizacao: {str(e)}")
        raise

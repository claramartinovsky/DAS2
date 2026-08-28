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
    logging.info('EL: itsm.chamado')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute(
            "SELECT id_chamado, nr_chamado, ds_tipo_chamado, ds_status_chamado, "
            "ds_prioridade, dt_criacao, dt_resolucao, dt_ultima_atualizacao, "
            "id_analista_atual, id_reporter, id_categoria, id_cliente_organizacao, "
            "id_fila_atual, ds_titulo, ds_descricao, dt_inclusao, dt_atualizacao, "
            "nm_sistema_origem, cd_registro_origem FROM itsm.chamado"
        )
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.chamado")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.chamado AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?))
              AS s(id_chamado, nr_chamado, ds_tipo_chamado, ds_status_chamado,
                   ds_prioridade, dt_criacao, dt_resolucao, dt_ultima_atualizacao,
                   id_analista_atual, id_reporter, id_categoria, id_cliente_organizacao,
                   id_fila_atual, ds_titulo, ds_descricao, dt_inclusao, dt_atualizacao,
                   nm_sistema_origem, cd_registro_origem)
        ON t.id_chamado = s.id_chamado
        WHEN MATCHED THEN
            UPDATE SET
                nr_chamado             = s.nr_chamado,
                ds_tipo_chamado        = s.ds_tipo_chamado,
                ds_status_chamado      = s.ds_status_chamado,
                ds_prioridade          = s.ds_prioridade,
                dt_criacao             = s.dt_criacao,
                dt_resolucao           = s.dt_resolucao,
                dt_ultima_atualizacao  = s.dt_ultima_atualizacao,
                id_analista_atual      = s.id_analista_atual,
                id_reporter            = s.id_reporter,
                id_categoria           = s.id_categoria,
                id_cliente_organizacao = s.id_cliente_organizacao,
                id_fila_atual          = s.id_fila_atual,
                ds_titulo              = s.ds_titulo,
                ds_descricao           = s.ds_descricao,
                dt_atualizacao         = s.dt_atualizacao,
                nm_sistema_origem      = s.nm_sistema_origem,
                cd_registro_origem     = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_chamado, nr_chamado, ds_tipo_chamado, ds_status_chamado,
                    ds_prioridade, dt_criacao, dt_resolucao, dt_ultima_atualizacao,
                    id_analista_atual, id_reporter, id_categoria, id_cliente_organizacao,
                    id_fila_atual, ds_titulo, ds_descricao, dt_inclusao, dt_atualizacao,
                    nm_sistema_origem, cd_registro_origem)
            VALUES (s.id_chamado, s.nr_chamado, s.ds_tipo_chamado, s.ds_status_chamado,
                    s.ds_prioridade, s.dt_criacao, s.dt_resolucao, s.dt_ultima_atualizacao,
                    s.id_analista_atual, s.id_reporter, s.id_categoria,
                    s.id_cliente_organizacao, s.id_fila_atual, s.ds_titulo,
                    s.ds_descricao, s.dt_inclusao, s.dt_atualizacao,
                    s.nm_sistema_origem, s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.chamado ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.chamado OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.chamado")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.chamado: {str(e)}")
        raise

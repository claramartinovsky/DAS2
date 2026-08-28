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
    logging.info('EL: itsm.chamado_status_historico')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute(
            "SELECT id_chamado_status_historico, id_chamado, ds_status_chamado, "
            "dt_inicio_status, dt_fim_status, qt_tempo_status_minutos, "
            "id_analista_responsavel, id_fila, dt_inclusao, dt_atualizacao, "
            "nm_sistema_origem, cd_registro_origem "
            "FROM itsm.chamado_status_historico"
        )
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.chamado_status_historico")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.chamado_status_historico AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?,?,?,?))
              AS s(id_chamado_status_historico, id_chamado, ds_status_chamado,
                   dt_inicio_status, dt_fim_status, qt_tempo_status_minutos,
                   id_analista_responsavel, id_fila, dt_inclusao, dt_atualizacao,
                   nm_sistema_origem, cd_registro_origem)
        ON t.id_chamado_status_historico = s.id_chamado_status_historico
        WHEN MATCHED THEN
            UPDATE SET
                id_chamado               = s.id_chamado,
                ds_status_chamado        = s.ds_status_chamado,
                dt_inicio_status         = s.dt_inicio_status,
                dt_fim_status            = s.dt_fim_status,
                qt_tempo_status_minutos  = s.qt_tempo_status_minutos,
                id_analista_responsavel  = s.id_analista_responsavel,
                id_fila                  = s.id_fila,
                dt_atualizacao           = s.dt_atualizacao,
                nm_sistema_origem        = s.nm_sistema_origem,
                cd_registro_origem       = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_chamado_status_historico, id_chamado, ds_status_chamado,
                    dt_inicio_status, dt_fim_status, qt_tempo_status_minutos,
                    id_analista_responsavel, id_fila, dt_inclusao, dt_atualizacao,
                    nm_sistema_origem, cd_registro_origem)
            VALUES (s.id_chamado_status_historico, s.id_chamado, s.ds_status_chamado,
                    s.dt_inicio_status, s.dt_fim_status, s.qt_tempo_status_minutos,
                    s.id_analista_responsavel, s.id_fila, s.dt_inclusao, s.dt_atualizacao,
                    s.nm_sistema_origem, s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.chamado_status_historico ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.chamado_status_historico OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.chamado_status_historico")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.chamado_status_historico: {str(e)}")
        raise

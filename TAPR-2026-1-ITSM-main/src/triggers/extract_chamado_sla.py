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
    logging.info('EL: itsm.chamado_sla')

    # ── EXTRACT ──────────────────────────────────────────────────────────────
    with _get_conn(
        os.getenv("SQL_SERVER_SOURCE"), os.getenv("SQL_DATABASE_SOURCE"),
        os.getenv("SQL_USER_SOURCE"), os.getenv("SQL_PASSWORD_SOURCE"),
    ) as src:
        cur = src.cursor()
        cur.execute(
            "SELECT id_chamado_sla, id_chamado, id_sla, fl_breach, "
            "qt_tempo_restante_minutos, qt_tempo_decorrido_minutos, qt_meta_minutos, "
            "dt_referencia, dt_inclusao, dt_atualizacao, nm_sistema_origem, "
            "cd_registro_origem FROM itsm.chamado_sla"
        )
        rows = cur.fetchall()

    logging.info(f"Extraídas {len(rows)} linhas de itsm.chamado_sla")
    if not rows:
        return

    # ── LOAD ─────────────────────────────────────────────────────────────────
    merge_sql = """
        MERGE itsm.chamado_sla AS t
        USING (VALUES (?,?,?,?,?,?,?,?,?,?,?,?))
              AS s(id_chamado_sla, id_chamado, id_sla, fl_breach,
                   qt_tempo_restante_minutos, qt_tempo_decorrido_minutos,
                   qt_meta_minutos, dt_referencia, dt_inclusao, dt_atualizacao,
                   nm_sistema_origem, cd_registro_origem)
        ON t.id_chamado_sla = s.id_chamado_sla
        WHEN MATCHED THEN
            UPDATE SET
                id_chamado                  = s.id_chamado,
                id_sla                      = s.id_sla,
                fl_breach                   = s.fl_breach,
                qt_tempo_restante_minutos   = s.qt_tempo_restante_minutos,
                qt_tempo_decorrido_minutos  = s.qt_tempo_decorrido_minutos,
                qt_meta_minutos             = s.qt_meta_minutos,
                dt_referencia               = s.dt_referencia,
                dt_atualizacao              = s.dt_atualizacao,
                nm_sistema_origem           = s.nm_sistema_origem,
                cd_registro_origem          = s.cd_registro_origem
        WHEN NOT MATCHED THEN
            INSERT (id_chamado_sla, id_chamado, id_sla, fl_breach,
                    qt_tempo_restante_minutos, qt_tempo_decorrido_minutos,
                    qt_meta_minutos, dt_referencia, dt_inclusao, dt_atualizacao,
                    nm_sistema_origem, cd_registro_origem)
            VALUES (s.id_chamado_sla, s.id_chamado, s.id_sla, s.fl_breach,
                    s.qt_tempo_restante_minutos, s.qt_tempo_decorrido_minutos,
                    s.qt_meta_minutos, s.dt_referencia, s.dt_inclusao, s.dt_atualizacao,
                    s.nm_sistema_origem, s.cd_registro_origem);
    """

    try:
        with _get_conn(
            os.getenv("SQL_SERVER_TARGET"), os.getenv("SQL_DATABASE_TARGET"),
            os.getenv("SQL_USER_TARGET"), os.getenv("SQL_PASSWORD_TARGET"),
        ) as dst:
            cur = dst.cursor()
            cur.execute("SET IDENTITY_INSERT itsm.chamado_sla ON")
            cur.executemany(merge_sql, [tuple(row) for row in rows])
            cur.execute("SET IDENTITY_INSERT itsm.chamado_sla OFF")
            dst.commit()
        logging.info(f"Carregadas {len(rows)} linhas em itsm.chamado_sla")
    except Exception as e:
        logging.error(f"Erro ao carregar itsm.chamado_sla: {str(e)}")
        raise

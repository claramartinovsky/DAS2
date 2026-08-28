import logging
import azure.functions as func

from triggers import (
    extract_fila,
    extract_categoria,
    extract_sla,
    extract_cliente_organizacao,
    extract_analista,
    extract_solicitante,
    extract_chamado,
    extract_chamado_sla,
    extract_chamado_status_historico,
    extract_csat_avaliacao,
)

app = func.Blueprint()


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False,
                   use_monitor=False)
def extract_all(myTimer: func.TimerRequest) -> None:
    logging.info("Iniciando pipeline EL")

    # Nível 1 — sem dependências de FK
    extract_fila.run()
    extract_categoria.run()
    extract_sla.run()
    extract_cliente_organizacao.run()

    # Nível 2 — dependem de fila e cliente_organizacao
    extract_analista.run()
    extract_solicitante.run()

    # Nível 3 — depende de fila, analista, solicitante, categoria, cliente_organizacao
    extract_chamado.run()

    # Nível 4 — dependem de chamado
    extract_chamado_sla.run()
    extract_chamado_status_historico.run()
    extract_csat_avaliacao.run()

    logging.info("Pipeline EL concluída")

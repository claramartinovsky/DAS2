# Design II -2026-2-ITSM

+ Integrantes: Guilherme T. Fiedler, Clara M. Martinovsky

A **CorpTech Soluções em TI Ltda.** é uma empresa de médio porte prestadora de serviços de TI gerenciados, com **85 colaboradores** e uma carteira de **40 clientes corporativos ativos**.
A equipe interna de **service desk** conta com **12 analistas**, distribuídos em dois níveis de suporte (**N1 e N2**), responsáveis por atender um volume médio de **1.400 chamados por mês**.
Em **2023**, a CorpTech implantou o **Jira Service Management (JSM)** como ferramenta oficial de **ITSM**, substituindo o controle anterior feito em planilhas. A adoção foi bem-sucedida: todos os chamados passaram a ser **registrados, categorizados e resolvidos dentro da ferramenta**, que já está em operação estável há mais de um ano.

---

# Problema Identificado

Apesar de toda a operação de suporte estar registrada no **Jira Service Management**, a liderança de TI da CorpTech enfrenta dificuldades para **extrair inteligência desses dados de forma ágil**.
Os relatórios nativos do JSM são **limitados e estáticos**, exigindo que a gerente de TI, **Patrícia**, exporte manualmente os dados em **arquivos CSV todas as semanas** para montar relatórios e apresentá-los nas reuniões.
O JSM tem os dados. O problema é que eles estão presos dentro da ferramenta — sem integração, sem histórico externo e sem a flexibilidade analítica que a liderança precisa para tomar decisões de operação e capacidade.
As principais dificuldades identificadas são:

| Área | Dificuldade relatada |
|-----|-----|
| **Gestão de SLA** | Não há visão consolidada de cumprimento de SLA por categoria, analista e cliente. Violações são identificadas apenas após o fechamento do chamado. |
| **Backlog e filas** | A distribuição de chamados em aberto por analista e nível de suporte só é visível dentro do JSM, sem um painel externo consolidado. |
| **Tendências e volume** | Não existe análise histórica de volume de chamados por período, picos de abertura ou sazonalidade. Decisões de dimensionamento são baseadas em percepção. |
| **Performance da equipe** | Métricas como **MTTR (Tempo Médio de Resolução)** e **MTTA (Tempo Médio de Resposta)** por analista não são monitoradas de forma sistemática. |
| **Satisfação do cliente** | O **CSAT** coletado no JSM não é cruzado com tipo de chamado, cliente ou analista, dificultando identificar onde a satisfação está abaixo do esperado. |

---

# Solução

A solução é um pipeline **EL (Extract & Load)** rodando em **Azure Functions** (Python), que copia periodicamente as tabelas do schema `itsm` de um banco de origem para um Azure SQL analítico, o qual alimenta o Power BI usado por Patrícia e pela liderança de TI.

```
src/
├── function_app.py
├── core/
│   ├── connection.py         # criação das conexões ODBC (origem e destino)
│   └── base_extractor.py     # classe base do processo EL
└── triggers/
    ├── extract_orchestrator.py   # timer trigger; dispara a pipeline a cada 5 min
    ├── extract_fila.py
    ├── extract_categoria.py
    ├── extract_sla.py
    ├── extract_cliente_organizacao.py
    ├── extract_analista.py
    ├── extract_solicitante.py
    ├── extract_chamado.py
    ├── extract_chamado_sla.py
    ├── extract_chamado_status_historico.py
    └── extract_csat_avaliacao.py
```

## Arquitetura do pipeline EL — padrão Template Method

Cada uma das dez tabelas segue exatamente a mesma sequência de passos: extrair da origem, verificar se há linhas, montar um `MERGE`, carregar no destino em lote e tratar erro. O que muda de uma tabela para outra é só o nome da tabela, a lista de colunas e a chave primária.

Para evitar repetir essa sequência dez vezes, o processo foi modelado com o padrão de projeto **Template Method** (GoF, comportamental): a classe `core.base_extractor.BaseExtractor` define o algoritmo completo no método `run()`, e cada arquivo em `triggers/extract_*.py` é uma subclasse que só declara `TABLE`, `PRIMARY_KEY` e `COLUMNS`.

```
BaseExtractor.run()
  ├─ extract()            extrai da origem
  ├─ transform(rows)       ponto de extensão (hook)
  └─ load(rows)            grava no destino via MERGE, em lote
```

O orquestrador (`extract_orchestrator.py`) chama as subclasses em quatro níveis, respeitando as dependências de chave estrangeira entre as tabelas.

## Variáveis de ambiente

A conexão com os bancos de origem e destino é configurada via variáveis de ambiente (`local.settings.json` local, ou Application Settings na Function App no Azure):

| Variável | Descrição |
|---|---|
| `SQL_SERVER_SOURCE` / `SQL_DATABASE_SOURCE` / `SQL_USER_SOURCE` / `SQL_PASSWORD_SOURCE` | Banco de origem (réplica do JSM) |
| `SQL_SERVER_TARGET` / `SQL_DATABASE_TARGET` / `SQL_USER_TARGET` / `SQL_PASSWORD_TARGET` | Banco de destino (Azure SQL analítico, consumido pelo Power BI) |

## Adicionando uma nova tabela

1. Criar `src/triggers/extract_<tabela>.py` com uma subclasse de `BaseExtractor` declarando `TABLE`, `PRIMARY_KEY` e `COLUMNS`.
2. Registrar a classe no nível correto de `PIPELINE`, em `extract_orchestrator.py`, respeitando a ordem de dependência de FK.

---
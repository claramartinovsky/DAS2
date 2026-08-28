É um serviço serverless que não necessita de servidor, funciona como uma lambda da AWS, precisamos apenas nos preocupar com o código e o servidor é configurado automaticamente. A função do Azure Functions nesse projeto vai ser tomar conta das tarefas agendadas e buscar dados via API e retornar os dados para o banco de dados. Esse serviço da Microsoft cobra apenas pelo tempo de execução e como precisamos de poucas execuções diárias ele acaba sendo uma boa opção. 

Referência: https://learn.microsoft.com/pt-br/azure/azure-functions/functions-overview

import logging
import azure.functions as func

app = func.FunctionApp()

from triggers.extract_orchestrator import app as orchestrator

app.register_functions(orchestrator)

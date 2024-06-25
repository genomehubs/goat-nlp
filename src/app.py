import logging
import os
import sys

import llama_index.core
import phoenix as px
from flask import Flask, render_template, request
from llama_index.core.agent import QueryPipelineAgentWorker
from llama_index.core.callbacks import CallbackManager
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from agent.query_pipeline import qp
from index import load_index

agent_worker = QueryPipelineAgentWorker(qp)
agent = agent_worker.as_agent(callback_manager=CallbackManager([]), verbose=True)

px.launch_app()
llama_index.core.set_global_handler("arize_phoenix")
endpoint = "http://127.0.0.1:6006/v1/traces"
tracer_provider = trace_sdk.TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))

LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

app = Flask("goat_nlp")

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)


@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/rebuildIndex")
def index():
    load_index(force_reload=True)


@app.route("/chat", methods=["POST"])
def chat():
    agent.reset()
    for _ in range(os.getenv("RETRY_LIMIT", 3)):
        try:
            response = agent.chat(request.form["user_input"] + "\nI only want the URL.")
            return {"url": str(response), "json_debug": ""}
        except Exception:
            continue
    return {"url": "", "json_debug": ""}


if __name__ == "__main__":
    app.run(debug=True)

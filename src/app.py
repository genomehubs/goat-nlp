import logging
import os
import sys

import llama_index.core
import phoenix as px
from flask import Flask, render_template, request
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from agent.query_pipeline import qp

Settings.llm = Ollama(
    model="llama3",
    base_url=os.getenv("OLLAMA_HOST_URL", "http://127.0.0.1:11434"),
    request_timeout=36000.0,
)

px.launch_app()
llama_index.core.set_global_handler("arize_phoenix")
endpoint = "http://127.0.0.1:6006/v1/traces"
tracer_provider = trace_sdk.TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))

LlamaIndexInstrumentor().instrument(tracer_provider=tracer_provider)

app = Flask("goat_nlp")

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

logger = logging.getLogger("goat_nlp.app")


@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/chat", methods=["POST"])
def chat():
    # agent.reset()
    for _ in range(os.getenv("RETRY_LIMIT", 3)):
        try:
            # response = agent.chat(request.form["user_input"])
            response = qp.run(input={"input": request.form["user_input"], "state": {}})
            logger.info(response)
            return {"url": str(response["state"]["final_url"]), "json_debug": ""}
        except Exception:
            continue
    return {"url": "", "json_debug": ""}


if __name__ == "__main__":
    app.run(debug=True)

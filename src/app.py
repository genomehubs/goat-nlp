import logging
import os
import sys
import json, time

import llama_index.core
from llama_index.core.llms import ChatMessage
import phoenix as px
from flask import Flask, render_template, request
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from flask import Response
from flask_cors import CORS
import threading, queue

from agent.query_pipeline import qp

Settings.llm = Ollama(
    model="llama3.1:8b-instruct-q4_0",
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
CORS(app)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

logger = logging.getLogger("goat_nlp.app")


@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    def stream_response(input):
        for _ in range(os.getenv("RETRY_LIMIT", 3)):
            state_queue = queue.Queue()
            current_state = {"done": False, "error": False, "exception": "", "state": ""}
            t1 = threading.Thread(
                target=lambda: qp.run(input={"input": input.split("#goat ")[1], "state": {"queue": state_queue}})
            )
            t1.start()
            while True:
                time.sleep(3)
                if not state_queue.empty():
                    temp_state = state_queue.get()
                    if current_state != temp_state:
                        print("State change")
                        current_state = temp_state
                        yield f"{json.dumps(current_state)}\n\n"
                        if current_state["done"]:
                            break
            if current_state["done"]:
                break

    return Response(stream_response(request.json["user_input"]), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True)

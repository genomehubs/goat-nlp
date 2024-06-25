import os

from llama_index.core.query_pipeline import QueryPipeline as QP
from llama_index.llms.ollama import Ollama

from agent.components import (
    agent_input_component,
    parse_react_output,
    process_agent_response,
    process_response,
    react_prompt_component,
    run_tool,
)

qp = QP(verbose=True)

qp.add_modules(
    {
        "agent_input": agent_input_component,
        "react_prompt": react_prompt_component,
        "llm": Ollama(
            model="llama3",
            base_url=os.getenv("OLLAMA_HOST_URL", "http://127.0.0.1:11434"),
            request_timeout=36000.0,
        ),
        "react_output_parser": parse_react_output,
        "run_tool": run_tool,
        "process_response": process_response,
        "process_agent_response": process_agent_response,
    }
)


qp.add_chain(["agent_input", "react_prompt", "llm", "react_output_parser"])


qp.add_link(
    "react_output_parser",
    "run_tool",
    condition_fn=lambda x: not x["done"],
    input_fn=lambda x: x["reasoning_step"],
)

qp.add_link(
    "react_output_parser",
    "process_response",
    condition_fn=lambda x: x["done"],
    input_fn=lambda x: x["reasoning_step"],
)

qp.add_link("process_response", "process_agent_response")
qp.add_link("run_tool", "process_agent_response")

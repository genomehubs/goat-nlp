import os

from llama_index.core.query_pipeline import QueryPipeline as QP
from llama_index.llms.ollama import Ollama

from agent.components import (
    construct_query,
    construct_url,
    identify_attributes,
    identify_entity,
    identify_index,
    identify_intent,
    identify_rank,
    identify_time_frame,
)

qp = QP(verbose=True)

qp.add_modules(
    {
        "llm": Ollama(
            model="llama3",
            base_url=os.getenv("OLLAMA_HOST_URL", "http://127.0.0.1:11434"),
            request_timeout=36000.0,
        ),
        "index": identify_index,
        "entity": identify_entity,
        "rank": identify_rank,
        "intent": identify_intent,
        "attribute": identify_attributes,
        "time": identify_time_frame,
        "query": construct_query,
        "url": construct_url,
    }
)


qp.add_chain(["intent", "index", "entity", "rank", "attribute", "time", "query", "url"])


# qp.add_link(
#     "react_output_parser",
#     "run_tool",
#     condition_fn=lambda x: not x["done"],
#     input_fn=lambda x: x["reasoning_step"],
# )

# qp.add_link(
#     "react_output_parser",
#     "process_response",
#     condition_fn=lambda x: x["done"],
#     input_fn=lambda x: x["reasoning_step"],
# )

# qp.add_link("process_response", "process_agent_response")
# qp.add_link("run_tool", "process_agent_response")

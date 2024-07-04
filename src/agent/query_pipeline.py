from llama_index.core.query_pipeline import QueryPipeline as QP

from agent.component_helpers import (
    construct_query,
    construct_url,
    identify_attributes,
    identify_entity,
    identify_index,
    identify_intent,
    identify_rank,
    identify_time_frame,
)
from agent.goat_query_component import GoatQueryComponent

qp = QP(verbose=True)

qp.add_modules(
    {
        "index": GoatQueryComponent(fn=identify_index),
        "entity": GoatQueryComponent(fn=identify_entity),
        "rank": GoatQueryComponent(fn=identify_rank),
        "intent": GoatQueryComponent(fn=identify_intent),
        "attribute": GoatQueryComponent(fn=identify_attributes),
        "time": GoatQueryComponent(fn=identify_time_frame),
        "query": GoatQueryComponent(fn=construct_query),
        "url": GoatQueryComponent(fn=construct_url),
    }
)


qp.add_chain(["intent", "index", "entity", "rank", "attribute", "time", "query", "url"])

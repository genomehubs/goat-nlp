from llama_index.llms.ollama import Ollama
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.response_synthesizers import BaseSynthesizer
from llama_index.core import PromptTemplate
from datetime import datetime


class GoaTAPIQueryEngine(CustomQueryEngine):

    retriever: BaseRetriever
    response_synthesizer: BaseSynthesizer
    llm: Ollama
    qa_prompt: PromptTemplate

    def custom_query(self, query_str: str, entity_taxon_map: dict):
        nodes = self.retriever.retrieve(query_str)

        context_str = "\n\n".join([n.node.get_content() for n in nodes])
        current_time = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        populated_prompt = self.qa_prompt.format(context_str=context_str, query_str=query_str,
                                  entity_taxon_map=entity_taxon_map,
                                  time=current_time)
        print(populated_prompt)
        response = self.llm.complete(
            populated_prompt
        )

        return str(response)

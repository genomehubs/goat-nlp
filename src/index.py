from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core import load_index_from_storage
from llama_index.core import get_response_synthesizer
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os
import json

from llama_index.core.schema import TextNode

from prompt import QUERY_PROMPT
from query_engine import GoaTAPIQueryEngine


load_dotenv()
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.llm = Ollama(
    model="codellama",
    base_url=os.getenv("OLLAMA_HOST_URL", "http://127.0.0.1:11434"),
    request_timeout=36000.0,
)
Settings.chunk_size = 256


def build_index(documents, save_dir="query_index", force=False):
    """
    Build the index from the given rich queries and save it in the specified
    directory.

    Parameters:
        - documents (list): A list of rich queries to build the index from.
        - save_dir (str): The directory path where the index will be saved.
            Defaults to "rich_query_index".
        - force (bool): If True, forces the index to be rebuilt even if the
            save directory already exists. Defaults to False.

    Returns:
        - query_index (VectorStoreIndex): The built index.

    Raises:
        - FileNotFoundError: If the save directory does not exist and force is
            set to False.
    """
    if not os.path.exists(save_dir) or force:
        query_index = VectorStoreIndex(documents)
        query_index.storage_context.persist(persist_dir=save_dir)
    else:
        query_index = load_index_from_storage(
            StorageContext.from_defaults(persist_dir=save_dir)
        )

    return query_index


def load_index(force_reload=False):
    """
    Load the index and query engine for the GoaT NLP system.

    Parameters:
        force_reload (bool): If True, force reload the index and rebuild it.
            Default is False.

    Returns:
        tuple: A tuple containing the index and query engine.

    """
    query_list = json.load(open("queries/script_generated_queries.json"))
    for x in query_list:
        x.pop("api_query", None)
    question_store = {x["english_query"]: x for x in query_list}

    index = build_index(
        [TextNode(text=x) for x in question_store.keys()], force=force_reload
    )
    retriever = index.as_retriever(similarity_top_k=5)
    synthesizer = get_response_synthesizer(response_mode="compact")

    query_engine = GoaTAPIQueryEngine(
        retriever=retriever,
        response_synthesizer=synthesizer,
        llm=Settings.llm,
        question_store=question_store,
        qa_prompt=QUERY_PROMPT,
    )

    return index, query_engine


index, query_engine = load_index()

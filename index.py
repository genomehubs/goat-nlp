from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core import load_index_from_storage
from llama_index.core import get_response_synthesizer
from llama_index.core import SimpleDirectoryReader
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import os

from prompt import QUERY_PROMPT
from query_engine import GoaTAPIQueryEngine


load_dotenv()
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.llm = Ollama(model="llama3", base_url=os.environ["OLLAMA_HOST_URL"],
                      request_timeout=36000.0)
Settings.chunk_size = 256


def build_index(documents,
                save_dir="rich_query_index",
                force=False):
    if not os.path.exists(save_dir):
        query_index = VectorStoreIndex.from_documents(
            documents
        )
        query_index.storage_context.persist(persist_dir=save_dir)
    else:
        query_index = load_index_from_storage(
            StorageContext.from_defaults(persist_dir=save_dir)
        )

    return query_index


def load_index(force_reload=False):
    documents = SimpleDirectoryReader(
        "rich_queries"
    ).load_data()

    index = build_index(documents, force=force_reload)
    retriever = index.as_retriever(similarity_top_k=3)
    synthesizer = get_response_synthesizer(response_mode="compact")

    query_engine = GoaTAPIQueryEngine(
        retriever=retriever,
        response_synthesizer=synthesizer,
        llm=Settings.llm,
        qa_prompt=QUERY_PROMPT,
    )

    return index, query_engine


index, query_engine = load_index()

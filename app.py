from flask import Flask, request, render_template, jsonify
from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import load_index_from_storage
from llama_index.core import SimpleDirectoryReader
from llama_index.llms.ollama import Ollama
from prompts.prompt_config import QUERY_PROMPT
import os, json


app = Flask(__name__)
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
Settings.llm = Ollama(model="llama3", base_url="", request_timeout=36000.0)


def build_index(documents,
                save_dir="rich_query_index"):
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


def wrap_with_prompt(query: str):
    return QUERY_PROMPT.format(query=query)


def chat_bot_rag(query):
    window_response = query_engine.query(
        wrap_with_prompt(query)
    )

    return window_response


documents = SimpleDirectoryReader(
    "rich_queries"
).load_data()

index = build_index(documents)

query_engine = index.as_query_engine(similarity_top_k=2)


@app.route('/')
def home():
    return render_template('chat.html')


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.form['user_input']
    bot_message = chat_bot_rag(user_message).response
    
    try:
        bot_message = json.loads(bot_message)["url"]
    except Exception as e:
        pass

    return jsonify({'response': str(bot_message)})


if __name__ == '__main__':
    app.run(debug=True)

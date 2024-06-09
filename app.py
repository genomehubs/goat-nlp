from flask import Flask, request, render_template, jsonify
from index import load_index, query_engine
from query_reformulation import fetch_related_taxons
import json


app = Flask(__name__)


def chat_bot_rag(query):
    entity_taxon_map = fetch_related_taxons(query)
    window_response = query_engine.custom_query(query,
                                                entity_taxon_map)

    return window_response


@app.route('/')
def home():
    return render_template('chat.html')


@app.route('/rebuildIndex')
def index():
    load_index(force_reload=True)


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.form['user_input']
    bot_message = chat_bot_rag(user_message)

    try:
        bot_message = json.loads(bot_message)["url"]
    except Exception:
        pass

    return jsonify({'response': str(bot_message)})


if __name__ == '__main__':
    app.run(debug=True)

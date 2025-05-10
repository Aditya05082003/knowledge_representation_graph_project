from flask import Flask, render_template, request, redirect, url_for
import os
import google.generativeai as genai
import networkx as nx
from pyvis.network import Network
import tempfile
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Function to extract relations using Gemini
def extract_relations_gemini(text):
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"""
    Analyze the following text and extract all important entity-relation-entity triplets.

    ⚡ Return the output ONLY in this exact JSON array format, without any explanation, without code block, without comments.
    [
    {{"subject": "Entity1", "relation": "Relationship", "object": "Entity2"}},
    ...
    ]

    Text:
    {text}
    """
    response = model.generate_content(prompt)
    return response.text

# Parse Gemini's response into a list of triples
def parse_relations(response_text):
    try:
        first_brace = response_text.find('[')
        if first_brace != -1:
            response_text = response_text[first_brace:]
        triples = json.loads(response_text)
        return triples
    except Exception as e:
        return []

# Build graph from triples
def build_graph(triples):
    g = nx.DiGraph()
    for triplet in triples:
        g.add_node(triplet['subject'])
        g.add_node(triplet['object'])
        g.add_edge(triplet['subject'], triplet['object'], label=triplet['relation'])
    return g

# Visualize the graph and save as HTML
def visualize_graph(g):
    net = Network(height="600px", width="100%", directed=True)
    net.from_nx(g)
    temp_dir = tempfile.mkdtemp()
    path = os.path.join(temp_dir, "graph.html")
    net.show_buttons(filter_=['physics'])
    net.save_graph(path)
    return path

# Extract text from uploaded PDF
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    return text

@app.route('/', methods=['GET', 'POST'])
def index():
    content = ""
    graph_html = None
    triples = []

    if request.method == 'POST':
        input_type = request.form.get('input_type')

        if input_type == 'Text':
            content = request.form.get('text_input')
        elif input_type == 'PDF File':
            file = request.files.get('pdf_file')
            if file:
                content = extract_text_from_pdf(file)

        if content.strip():
            response_text = extract_relations_gemini(content)
            triples = parse_relations(response_text)

            if triples:
                g = build_graph(triples)
                graph_path = visualize_graph(g)
                with open(graph_path, 'r', encoding='utf-8') as f:
                    graph_html = f.read()

    return render_template('index.html', graph_html=graph_html, triples=triples)

if __name__ == '__main__':
    app.run(debug=True)

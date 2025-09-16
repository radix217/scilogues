from flask import Flask, render_template, jsonify
import os
import sys

try:
    from ontology.ontology_tree import read_nodes, read_edges
except Exception:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ontology_tree import read_nodes, read_edges

base_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, 'templates'),
    static_folder=os.path.join(base_dir, 'static'),
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    nodes_csv = os.path.join(os.path.dirname(base_dir), 'graph', 'tree.csv')
    edges_csv = os.path.join(os.path.dirname(base_dir), 'graph', 'tree_edges.csv')
    nodes = read_nodes(nodes_csv)
    edges = read_edges(edges_csv)
    nodes_payload = [
        {
            'id': n.id,
            'label': n.topic,
            'parentid': n.parentid,
            'depth': int(getattr(n, 'depth', 0) or 0),
        }
        for n in nodes
    ]
    links_payload = [
        {
            'source': e.parentid,
            'target': e.childid,
        }
        for e in edges
    ]
    return jsonify({'nodes': nodes_payload, 'links': links_payload})


def run(debug: bool = True):
    app.run(debug=debug)


if __name__ == '__main__':
    run(debug=True)

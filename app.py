from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
from ontology_tree import generate_tree_live

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

def tree_generator_thread():
    generate_tree_live(socketio, 'tree.csv', max_nodes=25000)

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Start the tree generation in a background thread
    # to avoid blocking the main server process.
    threading.Thread(target=tree_generator_thread).start()

if __name__ == '__main__':
    socketio.run(app, debug=True)

import time
import webview
from flask import Flask, render_template, jsonify, request
import threading
from aws_manager import AWSManager
import logging

# Setup Flask
app = Flask(__name__)
app.debug = True  # Attiva il debug di Flask
app.config['DEBUG'] = True  
aws_manager = AWSManager()

# Store active connections
active_connections = []

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Set specific log levels for different components
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)



# Importa le routes dopo aver creato app e aws_manager
from routes import *

def run_server():
    app.run(
        host='127.0.0.1', 
        port=5000, 
        debug=False,  # With webview set False
        use_reloader=False
        
)

def create_application():
    server = threading.Thread(target=run_server)
    server.daemon = True
    server.start()
    
    # Wait a bit for the server to start
    time.sleep(1)
    
    webview.create_window(
        title='SSM Manager',
        url='http://127.0.0.1:5000',
        width=1200,
        height=800,
        resizable=True
    )
    webview.start()

if __name__ == '__main__':
    create_application()
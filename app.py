from flask import Flask, render_template, request, jsonify
import socket
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

scanning = False
queue = Queue()

def check_credentials(username, key):
    return username == "skibi" and key == "1234"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    username = request.form.get('username')
    key = request.form.get('key')
    if check_credentials(username, key):
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid username or key! Use username "skibi" and key "1234"'})

@app.route('/scan', methods=['POST'])
def start_scan():
    global scanning, queue
    if scanning:
        return jsonify({'error': 'Scan already in progress'})

    target = request.form.get('target')
    start_port = int(request.form.get('start_port'))
    end_port = int(request.form.get('end_port'))

    if not target or start_port <= 0 or end_port <= 0 or start_port > end_port:
        return jsonify({'error': 'Invalid input'})

    try:
        host = socket.gethostbyname(target)
    except:
        return jsonify({'error': 'Invalid host'})

    scanning = True
    queue = Queue()  # Reset queue
    threading.Thread(target=scan_ports, args=(host, start_port, end_port)).start()
    return jsonify({'success': True})

@app.route('/stop', methods=['POST'])
def stop_scan():
    global scanning
    scanning = False
    return jsonify({'success': True})

@app.route('/results')
def get_results():
    results = []
    while not queue.empty():
        results.append(queue.get())
    return jsonify({'results': results, 'scanning': scanning})

def scan_port(host, port):
    global scanning
    if not scanning:
        return
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((host, port))
        if result == 0:
            queue.put(f"Port {port} is open")
        sock.close()
    except Exception as e:
        queue.put(f"Error scanning port {port}: {str(e)}")

def scan_ports(host, start_port, end_port):
    global scanning
    max_workers = min(100, (end_port - start_port + 1))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(scan_port, host, port) 
                   for port in range(start_port, end_port + 1) if scanning]
        for future in futures:
            future.result()
    scanning = False

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
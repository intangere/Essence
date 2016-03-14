from flask import Flask, render_template, request, send_file, make_response
from WebSocket import WebSocket, Client
from multiprocessing import Process
from gevent.wsgi import WSGIServer
import random, string, os
from irc import IRC

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__,template_folder=tmpl_dir)

webSocket = WebSocket()
webSocket.config({'origin_port' : 8888,
				  'origin_host' : '127.0.0.1',
				  'websocket_host' : '127.0.0.1',
				  'websocket_port' : 8976
				})

@webSocket.onConnect #Handle the webSocket Connection, return Client() obj if auth successful
def handler(*args, **kwargs): #Handle the client connection, do whatever you want here
	ID = args[0]
	client = args[1]
	IRC(client, ID)
	del webSocket.clients[ID]
	webSocket.log("INFO", "Connection with %s ended" % ID)

def loop():
	webSocket.running = True
	while webSocket.running:
		handler()
		webSocket.log("INFO","Handler initiated")

@app.route('/client.html')
def index():
	ID = ''.join(random.SystemRandom().choice(
					   string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(20))
	webSocket.createID(ID)
	return render_template('client.html', ID=ID, port=webSocket.websocket_port)

@app.route('/favicon.ico')
def get_favicon():
	return send_file("images/favicon.ico", mimetype='image/ico')

p = Process(target=loop, args=()).start()
#app.run(debug=True, port=8888)
http_server = WSGIServer(('', 8888), app)
http_server.serve_forever()

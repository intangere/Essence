from flask import Flask, redirect, render_template, request, send_file, Markup, g
import sqlite3 as lite
import time
import os, subprocess
import random, string, aes, base64, sys
from NTRU.main import *
from logger import log
from contacts import contacts
from Wsx.WebSocket import WebSocket, Client
from multiprocessing import Process
import sys
import os.path
import socket
import thread
import time
import select
import random
import string
#############################################
#				  Essence				    #
#				 Web-Client				    #
#										    #
#				By Photonic				    #
#############################################
#Perhaps make this self distributional
#Make it pull NTRU.py from a server 
#Make it pull aes.py from a server
#Make it pull poly.py from a server


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__,template_folder=tmpl_dir)

webSocket = WebSocket()
webSocket.config({'origin_port' : 8888,
				  'origin_host' : '127.0.0.1',
				  'websocket_host' : '127.0.0.1',
				  'websocket_port' : 8976
				})

class Core():

	def __init__(self):
		self.s = socket.socket()
		self.pub = self.loadPubKey()
		self.priv = ''
		self.params = ''
		self.g = ''
		self.authenticated = False
		self.n = NTRU()
		self.ran = False
		self.webSocket = WebSocket()

	def loadPubKey(self):
		try:
			f = open('keys/pub.key', 'r')
			p = f.read().strip()
			f.close()
			return p
		except Exception as e:
			p = None
			return p

	def messageReceived(self, data):
	  if self.authenticated == True:
		data = data.split('|')
		msg = base64.b64decode(self.n.decryptParts(self.params, eval(data[3].replace('\r\n', ''))))
		if 'Ex%s' % data[1] in contacts.values():
		  for k,v in contacts.iteritems():
			if v == 'Ex%s' % data[1]:
			  #log('%s' % k, msg)
			  return '%s:%s' %(k, msg)
		else:
		  #log('Ex%s' % data[1], msg)
		  return '%s:%s' % (data[1], msg)
	  else:
		log("ERROR", "ACCESS DENIED")
		sys.exit(1)

	def authRequest(self, data):
		self.n.f = self.priv
		self.n.g = self.g
		self.n.d = self.priv.count(1) - 1
		msg = self.n.decryptParts(self.params, eval(data[1]))#n.splitNthChar(7, base64.b64decode(msg)))
		if msg.endswith('.'): 
			msg = msg[:-1]
			log("AUTH", "Auth token: %s" % msg)
			self.s.send('auth-ret %s %s\r\n' % (msg.strip(), self.pub.strip()))

	def setAuthTrue(self):
		self.authenticated = True
		log("LOGIN","Success. You have been authenticated")

	def connectionLoop(self, client, connected, priv, ID):
		if not self.priv:
			self.loadPrivAndg(self.loadAndShred())
		self.s.close()
		self.s = socket.socket()
		self.s.connect(("127.0.0.1", 4324))
		self.s.sendall('auth-req %s\r\n' % (self.pub))
		self.flag = False
		web_auth = False
		outputs = []
		inputs = [0, self.s, client.sock]
		buffer = ""
		while not self.flag:
			try:
				inputready, outputready, exceptrdy = select.select(inputs, outputs,[], 2)
				for i in inputready:
					if i == self.s:
					  if '\r\n' not in buffer:
						char = self.s.recv(1)
						if not char:
							self.flag = True
							break
						else:
							 buffer = ''.join([buffer, char])
					  else:
						if buffer.startswith('message|'):
						  msg = self.messageReceived(buffer)
						  webSocket.sendUpdate(client, msg, 'NORMAL')
						elif ' ' in buffer:
						  data = buffer.strip().replace('\r\n', '').split(' ', 1)
						else:
						  data = buffer
						buffer = ""
						if data[0] == 'auth':
						  self.authRequest(data)
						elif 'auth-success' in data:
						  self.setAuthTrue()
						else:
							pass
					if i == client.sock:
						data = client.sock.recv(1024)
						if data:
							data = data.strip()
							data_decoded = self.webSocket.decodeBytes(data.strip())
							if data_decoded.startswith('message'):
								self.sendMessage(data_decoded)
							elif data_decoded.startswith('shred'):
								self.flag = True
								client.sock.close()
								self.shred()
						else:
							inputs.remove(client.sock)
							connected = False
							client.sock.close()
							del webSocket.clients[ID]
							webSocket.log("INFO", "Connection with %s ended" % ID)
			except KeyboardInterrupt:
				print 'Interrupted.'
				self.s.close()
				break
		self.s.close()
		log("DEAD", "Connection to Essence has died.")
		self.exit()

	def shred(self):
		files = ['keys/priv.key', 'keys/pub.key', 'keys/g.txt', 'contacts.py']
		for file in files:
			f = open('%s' % file, 'r')
			p = len(f.read())
			f.close()
			for i in range(0, 4):
				f = open('%s' % file, 'w+')
				f.write(''.join(string.lowercase for x in range(p)))
				f.close()
			os.remove(file)


	def exit(self):
		self.s.close()
		log("INFO", "All connections killed.")
		log("INFO", "Essence has shut down.")
		sys.exit(1)

	def sendMessage(self, line):
		if contacts.has_key(line.split(' ', 1)[1].split(' ', 1)[0]):
		  line = 'message %s %s'.strip() % (contacts[line.split(' ', 1)[1].split(' ', 1)[0]], line.split(' ', 1)[1].split(' ', 1)[1])
		reciever, params = base64.b64decode(line.split(' ', 1)[1].split(' ', 1)[0][2:]).split('|')
		reciever, params = eval(reciever), eval(params)
		reciever_plain = line.split(' ',1 )[1].split(' ', 1)[0].split(' ')[0][2:]
		msg = line.split(' ',1)[1].split(' ', 1)[1]
		self.s.send('message|%s|%s|%s\r\n' % (self.pub, reciever_plain, self.n.encryptParts(params, reciever, self.n.splitNthChar(1, base64.b64encode(msg)))))

	def addContact(self, line):
		user, pub_key = line.split(' ')[1].strip(), line.split(' ')[2].strip()
		if not contacts.has_key(user) and pub_key not in contacts.values():
		  contacts[user] = pub_key
		  log('ADDED', '%s has been added with public key %s' % (user, pub_key))
		  f = open('contacts.py', 'w+')
		  f.write('contacts = %s' % str(contacts))
		  f.close()
		else:
		  log('ADDED', 'Something went wrong. Try again.. (The user may already be in your contacts)')

	def delContact(self, line):
		user = line.split(' ')[1].strip()
		if contacts.has_key(user):
		  del contacts[user]
		  f = open('contacts.py', 'w+')
		  f.write('contacts = %s' % str(contacts))
		  f.close()
		  log('DELETED', '%s has been removed from your contacts' % (user))
		else:
		  log('ERROR', '%s is not in your contacts' % user)

	def getContacts(self):
		for contact, key in contacts.iteritems():
		  log("CONTACT", 'Username: %s -> Public Key: %s' % (contact, key))  
		return contacts 

	def passToAesKey(self, password):
		key = password
		i = 0
		temp_key = ""
		while len(temp_key) < 32:
		  temp_key = "%s%s" % (temp_key, key[i])
		  if i == len(key) - 1:
			i = 0
		  else:
			i += 1
		return temp_key

	def loadAndShred(self):
		f = open('00z', 'r')
		pwd = f.read()
		f.close()
		f = open('00z', 'w+')
		f.write('0'*len(pwd))
		f.close()
		return pwd

	def loadPrivAndg(self, pwd):
		f = open('keys/priv.key', 'r')
		priv = eval(aes.decryptData(pwd, base64.b64decode(f.read().strip())))
		f.close()	
		f = open('keys/g.txt', 'r')
		g = eval(aes.decryptData(pwd, base64.b64decode(f.read().strip())))
		f.close()	
		if self.pub == None:
			self.pub = self.loadPubKey()			
		params = eval(base64.b64decode(self.pub).split('|')[1])
		self.priv = priv
		self.g = g
		self.params = params
		pwd = '0' * len(pwd)

essence = Core()

@app.route('/me')
def me():
	f = open('00z', 'r')
	t = f.read()
	f.close()
	if '0' * len(t) == t.strip():
		return redirect('/')
	ID = ''.join(random.SystemRandom().choice(
					   string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(20))
	if essence.authenticated == False:
		pass
		#\p = Process(target=essence.connectionLoop, args=()).start()
	webSocket.createID(ID)
	return render_template('me.html', ID=ID, port=webSocket.websocket_port, pubkey = essence.pub, contacts = contacts)

@app.route('/')
def index():
	if os.path.exists('keys/pub.key') and os.path.exists('keys/priv.key'):
		return render_template('login.html', pubkey = essence.pub)
	else:
		return render_template('create.html')

@app.route('/create', methods=['post'])
def create_acc():
	if request.form['password'] == request.form['confirm-password']:
		pwd = request.form['password']
		if len(pwd) > 6:
		  log("INFO", "Password is good")
		else:
			problem = "Password is shorter than 7 characters"
		  	return render_template('problem.html', problem = problem)
		pwd = essence.passToAesKey(pwd)
		essence.pub, essence.priv, essence.params, essence.g = essence.n.generateNTRUKeysAlpha()
		log('Public Key', essence.pub)
		essence.pub = base64.b64encode('%s|%s' % (essence.pub, str(essence.params).replace(' ', '')))
		log("INFO", "Your generated public key is Ex%s" % essence.pub)
		f = open('keys/pub.key' , 'w+')
		f.write(essence.pub)
		f.close()
		log('Params', str(essence.params))
		f = open('keys/priv.key' , 'w+')
		f.write(base64.b64encode(aes.encryptData(pwd, str(essence.priv))))
		f.close()
		f = open('keys/g.txt' , 'w+')
		f.write(base64.b64encode(aes.encryptData(pwd, str(essence.g))))
		f.close()
		f = open('contacts.py' , 'w+')
		f.write('contacts = {\'Me\' : \'Ex%s\'}' % essence.pub)
		f.close()
		contacts = {'Me' : essence.pub}
		log('INFO', 'Your Essence account is ready for use.')
		return render_template('login.html', pubkey=essence.pub)

@app.route('/login', methods=['post'])
def login():
	pwd = essence.passToAesKey(request.form['password'].strip().replace(u'\xbe', '').replace(u'\x7f', ')'))
	try:
		essence.ran = True
		f = open('keys/priv.key', 'r')
		priv = eval(aes.decryptData(pwd, base64.b64decode(f.read().strip())))
		essence.priv = priv
		f.close()	
		f = open('00z', 'w+')
		f.write(pwd)
		f.close()
	except Exception as e:
		print e
		return render_template('problem.html', problem = 'Incorrect decryption password entered.')
	return redirect('/me')# pubkey = pub)

@app.route('/register')
def register():
	return render_template("register.html")

@app.route('/styles.css')
def get_styles_css():
	return send_file("templates/styles.css", mimetype='css')

@app.route('/favicon.ico')	
def get_favicon():
	return "x"
	#return send_file("images/favicon.ico", mimetype='image/ico')

@app.route('/notes', methods=['get'])
def note():
	if request.args.has_key('user'):
		username = request.args.get('user')
		notes = getNotes(username)
		return render_template('notes.html', notes=notes)
	else:
		return render_template('post_note.html')

@app.route('/problem')
def problem():
	return render_template('problem.html') 

@app.route("/shutdown", methods=["GET"])
def logout():
	"""Logout the current user."""
	user = current_user
	user.authenticated = False
	logout_user()
	return render_template("/login.html")

@app.route("/shred", methods=["GET"])
def shred():
	"""Logout the current user."""
	user = current_user
	user.authenticated = False
	logout_user()
	return render_template("/login.html")


@webSocket.onConnect #Handle the webSocket Connection, return Client() obj if auth successful
def handler(*args, **kwargs): #Handle the client connection, do whatever you want here
	ID = args[0]
	client = args[1]
	connected = True
	essence.connectionLoop(client, connected, essence.priv, ID)

def loop():
	webSocket.running = True
	webSocket.log("INFO","Handler initiated")
	while webSocket.running:
		handler()


p = Process(target=loop, args=()).start()


app.debug = True
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = "jw09mrhcw0e8agv0a8fmsgd08vfag0sfmd0"
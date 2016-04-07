from flask import Flask, redirect, render_template, request, send_file, Markup
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
#############################################
#                  Essence                  #
#                 Web-Client                #
#                                           #
#                By Photonic                #
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

@webSocket.onConnect #Handle the webSocket Connection, return Client() obj if auth successful
def handler(*args, **kwargs): #Handle the client connection, do whatever you want here
	ID = args[0]
	client = args[1]
	connected = True
	while connected:
		data = client.sock.recv(1024)
		if data:
			data = data.strip()
		else:
			connected = False

	del webSocket.clients[ID]
	webSocket.log("INFO", "Connection with %s ended" % ID)

def loop():
	webSocket.running = True
	while webSocket.running:
		handler()
		webSocket.log("INFO","Handler initiated")

p = Process(target=loop, args=()).start()

memory = {'pub' : '',
		  'priv' : '',
		  'params' : '',
		  'g' : '',
		  'authenticated' : False,
		  's' : socket.socket()}

"""
Global variables
"""
try:
	f = open('keys/pub.key', 'r')
	memory['pub'] = f.read().strip()
	f.close()
except Exception as e:
	pub = None

n = NTRU()
"""
end
"""

def messageReceived(data):
  if authenticated == True:
    data = data.split('|')
    msg = base64.b64decode(n.decryptParts(params, eval(data[3].replace('\r\n', ''))))
    if 'Ex%s' % data[1] in contacts.values():
      for k,v in contacts.iteritems():
        if v == 'Ex%s' % data[1]:
          log('%s' % k, msg)
    else:
      log('Ex%s' % data[1], msg)
  else:
    log("ERROR", "ACCESS DENIED")
    sys.exit(1)

def authRequest(data):
	n.f = memory['priv']
	n.g = memory['g']
	n.d = memory['priv'].count(1) - 1
	msg = n.decryptParts(memory['params'], eval(data[1]))#n.splitNthChar(7, base64.b64decode(msg)))
	if msg.endswith('.'): 
		msg = msg[:-1]
		log("AUTH", "Auth token: %s" % msg)
		memory['s'].send('auth-ret %s %s\r\n' % (msg.strip(), memory['pub'].strip()))

def setAuthTrue():
    memory['authenticated'] = True
    log("LOGIN","Success. You have been authenticated")

def connectionLoop():
    memory['s'].close()
    memory['s'] = socket.socket()
    memory['s'].connect(("127.0.0.1", 4324))
    memory['s'].send('auth-req %s\r\n' % (memory['pub']))
    buffer = ""
    while True:
      if '\r\n' not in buffer:
        buffer = buffer + memory['s'].recv(1)
      else:
        if buffer.startswith('message|'):
          messageReceived(buffer)
        elif ' ' in buffer:
          data = buffer.strip().replace('\r\n', '').split(' ', 1)
        else:
          data = buffer
        buffer = ""
        if data[0] == 'auth':
          authRequest(data)
        elif 'auth-success' in data:
          setAuthTrue()

def exit():
    s.close()
    log("INFO", "All connections killed.")
    log("INFO", "Essence has shut down.")
    sys.exit(1)   

def sendMessage(line):
    if contacts.has_key(line.split(' ', 1)[1].split(' ', 1)[0]):
      line = 'message %s %s' % (contacts[line.split(' ', 1)[1].split(' ', 1)[0]], line.split(' ', 1)[1].split(' ', 1)[1])
    reciever, params = base64.b64decode(line.split(' ', 1)[1].split(' ', 1)[0][2:]).split('|')
    reciever, params = eval(reciever), eval(params)
    reciever_plain = line.split(' ',1 )[1].split(' ', 1)[0].split(' ')[0][2:]
    msg = line.split(' ',1)[1].split(' ', 1)[1]
    s.send('message|%s|%s|%s\r\n' % (memory['pub'], reciever_plain, n.encryptParts(params, reciever, n.splitNthChar(1, base64.b64encode(msg)))))

def addContact(line):
    user, pub_key = line.split(' ')[1].strip(), line.split(' ')[2].strip()
    if not contacts.has_key(user) and pub_key not in contacts.values():
      contacts[user] = pub_key
      log('ADDED', '%s has been added with public key %s' % (user, pub_key))
      f = open('contacts.py', 'w+')
      f.write('contacts = %s' % str(contacts))
      f.close()
    else:
      log('ADDED', 'Something went wrong. Try again.. (The user may already be in your contacts)')

def delContact(line):
    user = line.split(' ')[1].strip()
    if contacts.has_key(user):
      del contacts[user]
      f = open('contacts.py', 'w+')
      f.write('contacts = %s' % str(contacts))
      f.close()
      log('DELETED', '%s has been removed from your contacts' % (user))
    else:
      log('ERROR', '%s is not in your contacts' % user)

def getContacts():
    for contact, key in contacts.iteritems():
      log("CONTACT", 'Username: %s -> Public Key: %s' % (contact, key))  
    return contacts 

def passToAesKey(password):
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

@app.route('/me')
def me():
	if not memory['priv']:
		return redirect('/')
	ID = ''.join(random.SystemRandom().choice(
					   string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(20))
	webSocket.createID(ID)
	if memory['authenticated'] == False:
		thread.start_new_thread(connectionLoop, ())
	return render_template('me.html', ID=ID, port=webSocket.websocket_port, pubkey = memory['pub'], contacts = contacts.keys())

@app.route('/')
def index():
	if os.path.exists('keys/pub.key') and os.path.exists('keys/priv.key'):
		return render_template('login.html', pubkey = memory['pub'])
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
		pwd = passToAesKey(pwd)
		memory['pub'], memory['priv'], memory['params'], memory['g'] = n.generateNTRUKeysAlpha()
		log('Public Key', memory['pub'])
		memory['pub'] = base64.b64encode('%s|%s' % (str(memory['pub']), str(memory['params']))).replace(' ', '')
		log("INFO", "Your generated public key is Ex%s" % memory['pub'])
		f = open('keys/pub.key' , 'w+')
		f.write(memory['pub'])
		f.close()
		log('Params', str(memory['params']))
		f = open('keys/priv.key' , 'w+')
		f.write(base64.b64encode(aes.encryptData(pwd, str(memory['priv']))))
		f.close()
		f = open('keys/g.txt' , 'w+')
		f.write(base64.b64encode(aes.encryptData(pwd, str(memory['g']))))
		f.close()
		f = open('contacts.py' , 'w+')
		f.write('contacts = {\'Me\' : "'%s'"}' % memory['pub'])
		f.close()
		contacts = {'Me' : memory['pub']}
		log('INFO', 'Your Essence account is ready for use.')
		return render_template('login.html', pubkey=memory['pub'])

@app.route('/login', methods=['post'])
def login():
	pwd = passToAesKey(request.form['password'])
	try:
		f = open('keys/priv.key', 'r')
		memory['priv'] = eval(aes.decryptData(pwd, base64.b64decode(f.read().strip())))
		f.close()    
		f = open('keys/g.txt', 'r')
		memory['g'] = eval(aes.decryptData(pwd, base64.b64decode(f.read().strip())))
	 	f.close()    
	except Exception as e:
		return render_template('problem.html', problem = 'Incorrect decryption password entered.')
	memory['params'] = eval(base64.b64decode(memory['pub']).split('|')[1])
	return redirect('/me')# pubkey = pub)

@app.route('/register')
def register():
	return render_template("register.html")

@app.route('/styles.css')
def get_styles_css():
	return send_file("templates/styles.css", mimetype='css')

@app.route('/favicon.ico')	
def get_favicon():
	return send_file("images/favicon.ico", mimetype='image/ico')


@app.route('/notes', methods=['get'])
def note():
	if request.args.has_key('user'):
		username = request.args.get('user')
		notes = getNotes(username)
		return render_template('notes.html', notes=notes)
	else:
		return render_template('post_note.html')

@app.route('/add_contact', methods=['post']) #Handle every post request
def process_post():
	post_type = request.form['type']
	if post_funcs.has_key(post_type):
		args = []
		try:
			args.append(request.form['username'])
		except Exception as e:
			args.append("test")
		try:
			args.append(request.form['content'])
		except Exception as e:
			print e
			return render_template('problem.html')
		result = post_funcs[post_type](args[0], args[1])
	return render_template('process.html', result = result)

@app.route('/problem')
def problem():
	return render_template('problem.html') 


@app.route('/send', methods=['POST'])
def send_message():
	print request
	if(check_user(request)):
		#return redirect('/me')
		print "dicked on"
		return 'success'
	else:
		print "fuce"
		return render_template('problem.html') 

@app.route('/del_contact', methods=['POST'])
def del_contact():
	if (request.form.has_key('username') and (request.form.has_key('password')) and (request.form['password'] == request.form['confirm-pass'])):
		username = request.form['username']
		password = passToAesKey(request.form['password'])
		auth_id = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(random.randint(0, 20)))
		enc_auth_id = base64.b64encode(aes.encryptData(password,auth_id))
		res = addUser(username, auth_id, enc_auth_id)
		if res == False:
			return render_template('problem.html') #Too lazy to setup username in use page.
		else:
			return render_template('success.html', user=username)
	else:
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

app.config["SECRET_KEY"] = "jw09mrhcw0e8agv0a8fmsgd08vfag0sfmd0"

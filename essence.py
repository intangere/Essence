import os, subprocess
import random, string, aes, base64, sys
from NTRU.main import *
from logger import log
from contacts import contacts
from Wsx.WebSocket import WebSocket, Client
import sys
import os.path
import socket
import thread
import time
import select

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
		except Exception as e:
			print e
			p = None
		return p

	def messageReceived(self, data):
	  if authenticated == True:
		data = data.split('|')
		msg = base64.b64decode(self.n.decryptParts(params, eval(data[3].replace('\r\n', ''))))
		if 'Ex%s' % data[1] in contacts.values():
		  for k,v in contacts.iteritems():
			if v == 'Ex%s' % data[1]:
			  log('%s' % k, msg)
		else:
		  log('Ex%s' % data[1], msg)
	  else:
		log("ERROR", "ACCESS DENIED")
		sys.exit(1)

	def authRequest(self, data):
		print "PRINTING"
		print self.user.get_priv()
		print self.user.get_g()
		print self.user
		print self.user.get_id()
		print "ENDED"
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

	def connectionLoop(self, client, connected, user):
		self.user = user
		self.s.close()
		self.s = socket.socket()
		self.s.connect(("127.0.0.1", 4324))
		self.s.sendall('auth-req %s\r\n' % (self.pub))
		self.flag = False
		outputs = []
		inputs = [0, self.s, client.sock]
		buffer = ""
		while not self.flag:
			try:
				#if self.data_pipe.empty() == False:
				#	print "called the data pipe"
				#	print data_pipe
				#	for data in data_pipe:
				#		self.s.send(data)
				#		del data_pipe[0]
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
						  self.messageReceived(buffer)
						elif ' ' in buffer:
						  data = buffer.strip().replace('\r\n', '').split(' ', 1)
						else:
						  data = buffer
						buffer = ""
						print 'printing data'
						print data
						if data[0] == 'auth':
						  self.authRequest(data)
						elif 'auth-success' in data:
						  self.setAuthTrue()
						else:
								print 'Useless data from Essence'
					if i == client.sock:
						data = self.webSocket.decodeBytes(client.sock.recv(1024))
						#print data
						if data:
							#try:
							#msg = essence.sendMessage(data)
							#essence.s.send(msg)
							pass
							#except Exception as e:
							#	print "Got a fat error"
							#	pass
						else:
							inputs.remove(client)
							connected = False
							client.close()
							del webSocket.clients[ID]
							webSocket.log("INFO", "Connection with %s ended" % ID)
			except KeyboardInterrupt:
				print 'Interrupted.'
				self.s.close()
				break
		self.s.close()
		log("DEAD", "Connection to Essence has died.")

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
		f = open('pipe', 'w')
		f.write('message|%s|%s|%s\r\n' % (self.pub, reciever_plain, self.n.encryptParts(params, reciever, self.n.splitNthChar(1, base64.b64encode(msg)))))
		f.close()

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

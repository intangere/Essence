import sys
import os.path
import os
#Perhaps make this self distributional
#Make it pull NTRU.py from a server 
#Make it pull aes.py from a server
#Make it pull poly.py from a server
from NTRU.main import *
import aes
import base64
import socket
import thread
import getpass
import time
import readline
from contacts import contacts

class Client(object):

  def __init__(self):
    os.system('clear')
    self.n = NTRU()
    self.intitiateLogin()
    self.pub, self.priv, self.params, self.g = self.checkIfExists()
    self.log("INFO", "Your public identifer is Ex%s" % self.pub)
    self.authenticated = False

  def log(self, info, msg):
    print "[%s]: %s" % (info, msg)

  def checkIfExists(self):
    if not os.path.isfile('keys/pub.key') and not os.path.isfile('keys/priv.key'):
      return self.genKeys()
    else:
      return self.loadKeys()

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

  def genKeys(self):
    self.log("INFO", "This is your first time running Essence.")
    self.log("INFO", "Please wait while your public/private key pair is generated.")
    self.log("INFO", "This should take between 5 seconds to a few minutes.")
    try:
      pub, priv, params, g = self.n.generateNTRUKeysAlpha()
    except Exception as e:
      print "Error"
    return self.saveKeys(pub, priv, params, g)

  def saveKeys(self, pub, priv, params, g):
    self.log("INFO", "This is your first time running Essence")
    self.log("INFO", "Please enter a password. Do NOT forget this password.")
    self.log("INFO", "It is not stored anywhere. Only you know it.")
    self.log("INFO", "It will be used to decrypt your private key everytime you open Essence.")
    pwd = getpass.getpass('Enter a STRONG password:')
    if len(pwd) > 6:
      self.log("INFO", "Password is good")
    else:
      self.log("ERROR", "Retard alert. This application is not for you")
      sys.exit(1)
    pwd = self.passToAesKey(pwd)
    self.log('Public Key', pub)
    pub = base64.b64encode('%s|%s' % (str(pub), str(params))).replace(' ', '')
    self.log("INFO", "Your generated public key is Ex%s" % pub)
    f = open('keys/pub.key' , 'w+')
    f.write(pub)
    f.close()
    self.log('Params', str(params))
    f = open('keys/priv.key' , 'w+')
    f.write(base64.b64encode(aes.encryptData(pwd, str(priv))))
    f.close()
    f = open('keys/g.txt' , 'w+')
    f.write(base64.b64encode(aes.encryptData(pwd, str(g))))
    f.close()
    return pub, priv, params, g

  def loadKeys(self):
    f = open('keys/pub.key', 'r')
    pubkey = f.read().strip()
    f.close()
    pwd = self.passToAesKey(getpass.getpass("Enter your password:"))
    f = open('keys/priv.key', 'r')
    priv = eval(aes.decryptData(pwd, base64.b64decode(f.read().strip())))
    f.close()    
    f = open('keys/g.txt', 'r')
    g = eval(aes.decryptData(pwd, base64.b64decode(f.read().strip())))
    f.close()    
    params = eval(base64.b64decode(pubkey).split('|')[1])
    return pubkey, priv, params, g

  def intitiateLogin(self):
    self.log("[WELCOME]", "Welcome to Essence")
    self.log("[LOGIN]", "Please Login")

  def messageReceived(self, data):
    if self.authenticated == True:
      data = data.split('|')
      msg = base64.b64decode(self.n.decryptParts(self.params, eval(data[3].replace('\r\n', ''))))
      if 'Ex%s' % data[1] in contacts.values():
        for k,v in contacts.iteritems():
          if v == 'Ex%s' % data[1]:
            self.log('%s' % k, msg)
      else:
        self.log('Ex%s' % data[1], msg)
    else:
      self.log("ERROR", "ACCESS DENIED")
      sys.exit(1)

  def authRequest(self, data):
    self.n.f = self.priv
    self.n.g = self.g
    self.n.d = self.priv.count(1) - 1
    msg = self.n.decryptParts(self.params, eval(data[1]))#self.n.splitNthChar(7, base64.b64decode(msg)))
    if msg.endswith('.'): msg = msg[:-1]
    self.log("AUTH", "Auth token: %s" % msg)
    self.s.send('auth-ret %s %s\r\n' % (msg.strip(), self.pub.strip()))

  def setAuthTrue(self):
    self.authenticated = True
    self.log("LOGIN","Success. You have been authenticated")

  def connectionLoop(self):
    self.s = socket.socket()
    self.s.connect(("127.0.0.1", 4324))
    self.s.send('auth-req %s\r\n' % (self.pub))
    buffer = ""
    while True:
      if '\r\n' not in buffer:
        buffer = buffer + self.s.recv(1)
      else:
        if buffer.startswith('message|'):
          self.messageReceived(buffer)
        elif ' ' in buffer:
          data = buffer.strip().replace('\r\n', '').split(' ', 1)
        else:
          data = buffer
        buffer = ""
        if data[0] == 'auth':
          self.authRequest(data)
        elif 'auth-success' in data:
          self.setAuthTrue()

  def exit(self):
    self.s.close()
    self.log("INFO", "All connections killed.")
    self.log("INFO", "Essence has shut down.")
    sys.exit(1)   

  def sendMessage(self, line):
    if contacts.has_key(line.split(' ', 1)[1].split(' ', 1)[0]):
      line = 'message %s %s' % (contacts[line.split(' ', 1)[1].split(' ', 1)[0]], line.split(' ', 1)[1].split(' ', 1)[1])
    reciever, params = base64.b64decode(line.split(' ', 1)[1].split(' ', 1)[0][2:]).split('|')
    reciever, params = eval(reciever), eval(params)
    reciever_plain = line.split(' ',1 )[1].split(' ', 1)[0].split(' ')[0][2:]
    msg = line.split(' ',1)[1].split(' ', 1)[1]
    self.s.send('message|%s|%s|%s\r\n' % (self.pub, reciever_plain, self.n.encryptParts(params, reciever, self.n.splitNthChar(1, base64.b64encode(msg)))))

  def addContact(self, line):
    user, pub_key = line.split(' ')[1].strip(), line.split(' ')[2].strip()
    if not contacts.has_key(user) and pub_key not in contacts.values():
      contacts[user] = pub_key
      self.log('ADDED', '%s has been added with public key %s' % (user, pub_key))
      f = open('contacts.py', 'w+')
      f.write('contacts = %s' % str(contacts))
      f.close()
    else:
      self.log('ADDED', 'Something went wrong. Try again.. (The user may already be in your contacts)')

  def delContact(self, line):
    user = line.split(' ')[1].strip()
    if contacts.has_key(user):
      del contacts[user]
      f = open('contacts.py', 'w+')
      f.write('contacts = %s' % str(contacts))
      f.close()
      self.log('DELETED', '%s has been removed from your contacts' % (user))
    else:
      self.log('ERROR', '%s is not in your contacts' % user)

  def getContacts(self):
    for contact, key in contacts.iteritems():
      self.log("CONTACT", 'Username: %s -> Public Key: %s' % (contact, key))  
    return contacts 

  def inputLoop(self):
    time.sleep(2)
    while True:
      line = raw_input("> ").strip()
      cmd = line.split(' ', 1)[0]
      if cmd == 'exit':
        self.exit()
      elif cmd == 'message':
        self.sendMessage(line)
      elif cmd == 'addcontact':
        self.addContact(line)
      elif cmd == 'delcontact':
        self.delContact(line)
      elif cmd == 'contacts':
        self.getContacts()
      else:
        self.log('INFO', 'Command not found')

  def inputCleaner(self):
    while True:
        time.sleep(3)
        sys.stdout.write('\r'+' '*(len(readline.get_line_buffer())+2)+'\r')
        sys.stdout.write('> ' + readline.get_line_buffer())
        sys.stdout.flush()

c = Client()
thread.start_new_thread(c.inputCleaner, ())
thread.start_new_thread(c.connectionLoop, ())
c.inputLoop()
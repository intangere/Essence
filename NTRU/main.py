#####################
#Copyright Intangere#
#####################

from ntru import *
import random
from random import randint
import aes, base64
import uuid
import string
import re

class NTRU(object):

	def __init__(self):
		self.ranPol=[-1,-1,1,1]
		self.d = randint(4,10)
		self.d1 = self.d+1
		self.f = self.randfArray()
		self.g = self.randgArray()
		self.idxs = {x:i for i,x in enumerate('.' + string.ascii_lowercase + string.ascii_uppercase + '=' + '+' + ' ' + string.digits)}
		self.ridxs = {i:x for i,x in enumerate('.' + string.ascii_lowercase + string.ascii_uppercase + '=' + '+' + ' ' + string.digits)}

	def randfArray(self):
		i = []
		for x in range(0,self.d):
			i.append(1)
		for x in range(0,self.d):
			i.append(-1)
		while len(i) < 128:
			i.append(randint(-128, 128))
		random.shuffle(i)
		return i					

	def randgArray(self):
		i = []
		for x in range(0,self.d):
			i.append(1)
		for x in range(0,self.d):
			i.append(-1)
		while len(i) < 128:
			i.append(randint(-128, 128))
		random.shuffle(i)
		return i		

	def RandomPrime(self, min, max):
  		while True:
    			n = random.randint(min, max)
			if n % 2 == 0:
      				continue;
	    		prime = True;
			for x in range(3, int(n**0.5 + 1), 2):
				if n % x == 0:
				        prime = False;        	
					break; 
    			if prime: 
				return n

	def generateNTRUKeys(self):
		while True:
			params = [7, self.RandomPrime(10, 99), self.RandomPrime(100000, 999999)]
			ntruObj = Ntru(params[0], params[1], params[2])
			ntruObj.genPublicKey(self.f,self.g,self.d)
			msg = [1,10,50,60,70]
			encMsg = self.encryptUsingPubKey(params, ntruObj.getPublicKey(), msg) 
			if msg == self.decryptUsingPrivKey(params, encMsg):
				return ntruObj.getPublicKey(), params
				break

	def generateNTRUKeysAlpha(self):
		while True:
			try:
				params = [7, self.RandomPrime(10, 99), self.RandomPrime(100000, 999999)]
				ntruObj = Ntru(params[0], params[1], params[2])
				ntruObj.genPublicKey(self.f,self.g,self.d)
				msg = [1,10,50,60,70]
				encMsg = self.encryptUsingPubKey(params, ntruObj.getPublicKey(), msg) 
				if msg == self.decryptUsingPrivKey(params, encMsg):
					return ntruObj.getPublicKey(), self.f, params, self.g #params
					break
			except Exception as e:
				print "Generating random key pair..."

	def encryptUsingPubKey(self, params, pub, msg):
		ntruObj = Ntru(params[0], params[1],params[2])
		ntruObj.setPublicKey(pub)
		encryptedMsg = ntruObj.encrypt(msg, self.ranPol)
		return encryptedMsg

	def decryptUsingPrivKey(self, params, msg):
		ntruObj = Ntru(params[0], params[1],params[2])
		ntruObj.genPublicKey(self.f,self.g,self.d)
		decryptedMsg = ntruObj.decrypt(msg)
		return decryptedMsg

	def splitNthChar(self, nth, msg):
		i = 0
		t = 0
		p = 0
		split = []
		split.append([])
		while i < len(msg):
			split[p].append(msg[i])
			if t == nth:
				t = 0
				p += 1
				split.append([])
			else:
				t += 1
			i += 1
		#split = re.findall(''.join('.' for x in range(0, nth)), msg)
		#split.append(msg[-1])
		return split

	def encryptParts(self, params, pub, parts):
		encryptedParts = []
		for part in parts:
			partIdxs = [self.idxs[x] for x in part]
			encryptedParts.append(self.encryptUsingPubKey(params, pub, partIdxs))
		return encryptedParts

	def decryptParts(self, params, parts):
		decryptedParts = []
		message = ""
		for part in parts:
			decryptedParts.append(self.decryptUsingPrivKey(params, part))
		#print decryptedParts
		for decryptedPart in decryptedParts:
			for x in decryptedPart:
				message = ''.join([message, self.ridxs[x]]) 
		return message



""" Example Usage
n = NTRU()
pub, params = n.generateNTRUKeys()
msg = "Hello world! I am intangere!"
aeskey = str(uuid.uuid4().hex)
aesMsg = base64.b64encode(aes.encryptData(aeskey, msg))
aesParts = n.splitNthChar(7, aesMsg)
encryptedParts = n.encryptParts(params, pub, aesParts)
decryptedParts = n.decryptParts(params, encryptedParts)
print "Pubkey: %s" % pub
print "Params: %s" % params
print "Message: %s" % msg
print "Aes Message: %s" % aesMsg
print "Ntru Parts: %s" % encryptedParts
print "Decrypted Message: %s" % decryptedParts
print "Decrypted Aes Message: %s" % aes.decryptData(aeskey, base64.b64decode(decryptedParts))
"""

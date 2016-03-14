#####################
#Copyright Intangere#
#####################
from main import NTRU
import base64
import uuid
import aes
from random import randint

n = NTRU()
i = 1
while i < 21:
	msg = str(randint(0, 999999999999999999999))
	pub, params = n.generateNTRUKeysAlpha()
	#msg = base64.b64encode("I like pie :^|")
	#msg = base64.b64encode(msg)
	#msg = [n.idxs[x] for x in msg]
	#aesParts = n.splitNthChar(128, msg)
	#print aesParts
	encrypted= n.encryptParts(params, pub, n.splitNthChar(5, msg))
	#encrypted = n.encryptUsingPubKey(params, pub, msg)
	decrypted_ = n.decryptParts(params, encrypted)
	"""
	print decrypted_
	#decryptedParts = n.decryptParts(params, encryptedParts)
	print "Pubkey: %s" % pub
	print "Params: %s" % params
	print "Message: %s" % msg
	print "Encrypted %s" % encrypted
	#print "Decrypted %s" % decrypted
	print "Decrypted_ %s" % base64.b64decode(decrypted_)
	"""
	if decrypted_ == msg:
		print "[Test %s]: SUCCESSFUL TEST" % i
	else:
		print "[Test %s]: FAILED TEST" % i
	i += 1

#print "Ntru Parts: %s" % encryptedParts
#print "Decrypted Message: %s" % decryptedParts
#print "Decrypted Aes Message: %s" % base64.b64decode(decryptedParts)

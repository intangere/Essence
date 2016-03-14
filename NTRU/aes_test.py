from NTRU.main import *
import base64
import aes
n = NTRU()
pub, params = n.generateNTRUKeys()
msg = "Hello world! I am intangere!"
aeskey = str(uuid.uuid4().hex)
aesMsg = base64.b64encode(aes.encryptData(aeskey, msg))
aesParts = n.splitNthChar(7, aesMsg)
print params
encryptedParts = n.encryptParts([71,29,491531], pub, aesParts)
decryptedParts = n.decryptParts(params, encryptedParts)
print "Pubkey: %s" % pub
print "Params: %s" % params
print "Message: %s" % msg
print "Aes Message: %s" % aesMsg
print "Ntru Parts: %s" % encryptedParts
print "Decrypted Message: %s" % decryptedParts
print "Decrypted Aes Message: %s" % aes.decryptData(aeskey, base64.b64decode(decryptedParts))

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
from NTRU.main import *
from NTRU.ntru import *

packets = {
    'message' : {
            'origin' : 1,
            'reciever' : 2,
            'message' : 3
            },
    'ping' : {
            'hashkey' : 1
            }
    }

class Chat(LineReceiver):
    def __init__(self, users):
        self.queue = [] #Store the "message org recv msg" 
        self.users = users

    def connectionMade(self):
        self.state = "Unauthenticated"
        self.user_auth_key = None

    def connectionLost(self, reason):
        print "Connection deadarino"
        if hasattr(self, 'pub_key'):
            if self.pub_key in self.users:
                del self.users[self.pub_key]

    def log(self, info, msg):
        print "[%s]: %s" % (info, msg)

    def lineReceived(self, line):
        print line
        line = line.replace('\r\n', '')
        if self.state == "Unauthenticated":
            if not "auth-ret" in line:
                self.auth_user(line)
            else:
                self.check_auth(line)
        else:
            self.packetHandler(line)
            
    def packetHandler(self, message):
        packet = message.split('|')
        self.log("MESSAGE", str(packet))
        print packet[1]
        print self.pub_key
        if packet[0] == "message":
            if packet[1] == self.pub_key:
                if ',' in packet[2]:
                    for user in packet[2].split(','):
                        if user.startswith('Ex'):
                            user = user[2:]
                        self.users[user].sendLine(message +'\r\n')
                else:
                    self.users[packet[2]].sendLine(message +'\r\n')
        elif packet[0] == "ping":
            self.sendLine(packet[1]) #packet[1] is the hashkey
        else:
            #self.transport.loseConnection()
            self.sendLine('Yolod\r\n')
            pass
        #We need to auth the user/perhaps every message
        #Make the client do work or else the message will be rejected ^
        #Queue messages

    def check_auth(self, line):
        if self.user_auth_key == line.split(' ')[1]:
            self.state = "Authenticated"
            self.log("AUTH-CHECK", line)
            self.pub_key = line.split(' ')[2]
            self.users[self.pub_key] = self
            #if self.queue.has_key(self.pub_key):
            #    for message in self.queue[self.pub_key]:
            #        packet = message.split(" ")
            #        self.users[packet[2]].sendLine(packet[3])
            #        time.sleep(.5)
            self.log("INFO", "%s has authenticated" % self.pub_key)
            self.sendLine('auth-success\r\n')
        else:
            self.log("DISCONNECTED", "Previous authentication event failed")
            self.transport.loseConnection()

    def auth_user(self, line):
        self.log("AUTH-REQUEST", line)
        self.user_auth_key = str(randint(0,999917))
        pub_key = self.buildKey(line.split(' ')[1])
        params = eval(base64.b64decode(line.split(' ')[1]).split('|')[1])
        self.N = NTRU()
        msg = self.N.encryptParts(params, pub_key, self.N.splitNthChar(1, self.user_auth_key))
        self.sendLine("auth %s\r\n" % msg)

    def buildKey(self, pub_key):
        return eval(base64.b64decode(pub_key).split('|')[0])

class ChatFactory(Factory):
    def __init__(self):
        self.users = {} #Store users

    def buildProtocol(self, addr):
        return Chat(self.users)

reactor.listenTCP(4324, ChatFactory())
reactor.run()

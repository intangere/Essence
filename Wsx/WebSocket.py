import socket, hashlib, re, base64, time
import random, os
from multiprocessing import Process

opcodes = { "NORMAL" : 0x1,
            "CLOSE" : 0X8,
            "PING" : 0X9,
            "PONG" : 0Xa }

code = 0x80

class WebSocket(object):

    def __init__(self):
        self.s = socket.socket()
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}
        self.running = False

    def config(self, config_options):
        self.origin_host = config_options['origin_host']
        self.origin_port = config_options['origin_port']
        self.websocket_host = config_options['websocket_host']
        self.websocket_port = config_options['websocket_port']
        self.s.bind((self.websocket_host, 0))
        self.s.listen(10);
        self.websocket_port = self.s.getsockname()[1]
        self.log("INFO", "[Port|%s|]: Listening for up to 10 connections.." % self.websocket_port)


    def log(self, info, message):
        print "[%s]:%s" % (info, message)

    def buildHeader(self, key):
        return ''.join([
            "HTTP/1.1 101 WebSocket Protocol Handshake\r\n",
            "Upgrade: WebSocket\r\n",
            "Connection: Upgrade\r\n",
            "Sec-WebSocket-Origin: http://%s:%s\r\n" % (self.origin_host, self.origin_port),
            "Sec-WebSocket-Location: ws://%s:%s/\r\n" % (self.websocket_host, self.websocket_port),
            "Sec-WebSocket-Accept: %s\r\n\r\n" % (key)])

    def onConnect(self, func):
        def run(*args, **kwargs):
            self.log("INFO", "Waiting for connection...")
            client, _ = self.s.accept()
            self.log("INFO", "Client accepted")
            ID = self.authClient(client)
            return Process(target=func, args=(ID, Client(client))).start()
        return run

    def parseHeaders(self, raw):
        return dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", raw))

    def buildFrame(self, buf, opcode):
        length = chr(len(buf))
        header = chr(code | opcodes[opcode])
        frame = "%s%s%s" % (header, length, buf)
        return frame

    def authClient(self, client):
        request = client.recv(1024)
        if '\r\n\r\n' in request:
            headers = self.parseHeaders(request)
            if headers.has_key('Sec-WebSocket-Key'):
                key = headers['Sec-WebSocket-Key']
                key = base64.b64encode(hashlib.sha1(key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
                client.send(self.buildHeader(key))
                self.log("INFO", "Headers built and sent...")
                ID = self.decodeBytes(client.recv(1024))
                self.log("AUTH", "Authenticated client with ID %s.." % ID)
                self.clients[ID] = client
                return ID

    def sendAll(self, data, opcode_type):
        for client in self.clients:
            client.send(self.buildFrame(data, opcode_type))

    def sendUpdate(self, data, opcode_type):
        if self.sock:
            self.sock.send(self.buildFrame(data, opcode_type))
        else:
            del self.clients[client]

    def createID(self, ID):
        self.clients[ID] = Client("")
        self.log("INFO", "[Uninitialized client with ID]: %s [Added]" % ID)

    def decodeBytes(self, stringStreamIn):
        byteArray = [ord(character) for character in stringStreamIn]
        datalength = byteArray[1] & 127
        indexFirstMask = 2 
        if datalength == 126:
            indexFirstMask = 4
        elif datalength == 127:
            indexFirstMask = 10
        masks = [m for m in byteArray[indexFirstMask : indexFirstMask+4]]
        indexFirstDataByte = indexFirstMask + 4
        decodedChars = []
        i = indexFirstDataByte
        j = 0
        while i < len(byteArray):
            decodedChars.append( chr(byteArray[i] ^ masks[j % 4]) )
            i += 1
            j += 1
        return ''.join(decodedChars)

class Client(WebSocket):

    def __init__(self, sock):
        self.sock = sock
     
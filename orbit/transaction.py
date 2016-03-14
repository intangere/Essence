from twisted.internet.defer import Deferred
from orbit.server import WebSocketConnection
import string
from random import choice


class State(object):
	def __init__(self):
		self.transaction = None

	def loadTransaction(self, transaction):
		self.transaction = transaction

	def onNewConnection(self, ws):
		pass

	def onUpdate(self, ws, opcode, data, fin):
		pass

	def onEndConnection(self, ws):
		pass

class Transaction(object):
	def __init__(self, stateObject, reverseProxyHeader=None):
		self.websockets = []
		self.state = stateObject
		self.state.loadTransaction(self)
		self.finished = Deferred()
		self.reverseProxyHeader = reverseProxyHeader

	def getWebSocket(self, request):
		transport, request.transport = request.transport, None
		protocol = WebSocketConnection(self.state)
		transport.protocol = protocol

		if self.reverseProxyHeader is not None:
			protocol.ip = request.getHeader(self.reverseProxyHeader)
		else:
			protocol.ip = transport.getPeer().host

		def handle_dc(obj):
			if obj in self.websockets:
				self.websockets.remove(obj)
				self.state.onEndConnection(obj)
			return obj
		protocol.finished.addCallback(handle_dc)
		self.websockets.append(protocol)
		protocol.makeConnection(transport)
		self.state.onNewConnection(protocol)
		protocol.pingLoop.start(20.0)

		return protocol

	def endWebSocket(self, websocket):
		if websocket.connected:
			websocket.transport.loseConnection()
		self.websockets.remove(websocket)
		self.state.onEndConnection(websocket)

	def getWebSockets(self, prerequisite = lambda x: True):
		for ws in self.websockets:
			if prerequisite(ws):
				yield ws

	def sendUpdate(self, data, prerequisite = lambda x: True):
		for ws in self.websockets:
			if not ws.connected:
				continue
			if not prerequisite(ws):
				continue
			ws.write(data)

	def finish(self):
		for val in self.websockets:
			val.transport.loseConnection()
		self.finished.callback(self)


class TransactionNotFoundException(Exception):
	pass

transaction_charset = string.letters+string.digits

class TransactionManager(object):
	def __init__(self):
		self.transactions = {}

	def addTransaction(self, transaction, rstr=None):
		if rstr is None:
			rstr = ''.join([choice(transaction_charset) for _ in xrange(32)])
		self.transactions[rstr] = transaction
		def finish_transaction(data):
			del self.transactions[rstr]
			return data
		transaction.finished.addCallback(finish_transaction)
		return rstr

	def hasTransaction(self, key):
		return self.transactions.has_key(key)

	def __call__(self, secretKey):
		if not self.transactions.has_key(secretKey):
			raise TransactionNotFoundException()
		return self.transactions[secretKey]

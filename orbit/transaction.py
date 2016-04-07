from twisted.internet.defer import Deferred
from orbit.server import WebSocketConnection
import string
from random import choice

class WSProtocol(object):
	def __init__(self, transaction):
		# note-- this is a circular reference, which is probably acceptable since a transaction shouldn't
		# ever be disposed while it still has connections associated with it, however keep in mind this
		# means the transaction/protocols will be stuck in scope if a protocol ever leaks
		self.transaction = transaction
		self.ws = None

	def makeConnection(self, ws):
		self.ws = ws
		self.connectionMade(ws)

	def connectionMade(self, ws):
		pass

	def dataReceived(self, opcode, data):
		pass

	def connectionEnd(self):
		pass

	def disconnect(self):
		self.transaction.connections[self].transport.abortConnection()

class Transaction(object):
	def __init__(self, protocol, reverseProxyHeader=None):
		self.protocol = protocol
		# map of protocol: underlying ws connection
		self.connections = {}

		self.finished = Deferred()
		self.reverseProxyHeader = reverseProxyHeader

		self.initialize()

	# convenience method to avoid having to call parent __init__
	def initialize(self):
		pass

	def _proto_disconnected(self, ws, proto):
		# TODO: is ws even available for writing here? this connection is presumably already terminated
		proto.connectionEnd(ws)
		del self.connections[proto]

	def getWebSocket(self, request):
		transport, request.transport = request.transport, None

		p = self.protocol(self)

		protocol = WebSocketConnection(p)
		self.connections[p] = protocol
		transport.protocol = protocol

		if self.reverseProxyHeader is not None:
			protocol.ip = request.getHeader(self.reverseProxyHeader)
		else:
			protocol.ip = transport.getPeer().host

		protocol.finished.addCallback(self._proto_disconnected)
		protocol.makeConnection(transport)

		p.makeConnection(protocol)

		protocol.pingLoop.start(20.0)

		return protocol

	def finish(self):
		for connection in self.connections.values():
			connection.transport.loseConnection()

		self.connections = {}

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

from twisted.internet.defer import Deferred
from twisted.web.resource import IResource, Resource
from twisted.web.server import NOT_DONE_YET
from orbit.framing import buildAccept, TEXT, PING
from orbit.protocol import WebSocketProtocol
from twisted.internet.task import LoopingCall
from zope.interface import implementer


class WebSocketReceiver(object):
	def __init__(self, connection):
		self.connection = connection
		self.transport = None

	def makeConnection(self, transport):
		self.transport = transport

	def closeReceived(self, statusCode, statusMessage):
		pass

	def frameReceived(self, opcode, data):
		self.connection.state.dataReceived(opcode, data)


class WebSocketConnection(WebSocketProtocol):
	def __init__(self, stateObject):
		self.state = stateObject
		self.opcode = TEXT
		WebSocketProtocol.__init__(self, WebSocketReceiver(self))
		self.finished = Deferred()
		self.pingLoop = LoopingCall(self.doPing)

	def doPing(self):
		self.receiver.transport.sendFrame(PING, '')

	def write(self, data):
		self.receiver.transport.sendFrame(self.opcode, data)

	def sendFrame(self, opcode, data):
		self.receiver.transport.sendFrame(opcode, data)

	def writeSequence(self, data):
		for chunk in data:
			self.write(chunk)

	def connectionLost(self, reason):
		if self.pingLoop.running:
			self.pingLoop.stop()
		self.finished.callback(self)

@implementer(IResource)
class WebSocketResource(object):
	# keyword is the name of the HTTP GET parameter used to look up a transaction, if one is needed
	# lookup is a function that accepts the result of the keyword param and returns a Transaction object or throws an exception if none is found
	def __init__(self, lookup, keyword=None):
		self.lookup = lookup
		self.keyword = keyword

	def getChildWithDefault(self, name, request):
		raise RuntimeError('Cannot get IResource children from WebSocketResource')

	def putChild(self, path, child):
		raise RuntimeError('Cannot put IResource children into WebSocketResource')

	def render(self, request):
		request.defaultContentType = None
		# If we fail at all, we'll fail with 400 and no response.
		failed = False
		if request.method != 'GET':
			failed = True

		upgrade = request.getHeader('Upgrade')
		if not upgrade or 'websocket' not in upgrade.lower():
			failed = True

		connection = request.getHeader('Connection')
		if not connection or 'upgrade' not in connection.lower():
			failed = True

		key = request.getHeader('Sec-WebSocket-Key')
		if not key:
			failed = True

		version = request.getHeader('Sec-WebSocket-Version')
		if not version or version != '13':
			failed = True
		request.setHeader('Sec-WebSocket-Version', '13')

		transaction = self.lookup(request.args[self.keyword][0] if (self.keyword is not None and request.args.has_key(self.keyword)) else None)

		if failed:
			request.setResponseCode(400)
			return ''

		request.setResponseCode(101)
		request.setHeader('Upgrade', 'WebSocket')
		request.setHeader('Connection', 'Upgrade')
		request.setHeader('Sec-WebSocket-Accept', buildAccept(key))

		request.write('')
		transaction.getWebSocket(request)


		return NOT_DONE_YET

class WSGISiteResource(Resource):
	def __init__(self, wsgiResource, children):
		Resource.__init__(self)
		self._wsgiResource = wsgiResource
		self.children = children

	def getChild(self, path, request):
		request.prepath.pop()
		request.postpath.insert(0, path)
		return self._wsgiResource
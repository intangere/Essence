from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.python import log

try:
	from orbit.encoding import packUShort
except ImportError:
	from orbit.pyencoding import packUShort

from orbit.framing import buildFrame, PONG, PING, CLOSE, parseFrames, NORMAL
from zope.interface import Interface

class IWebSocketFrameReceiver(Interface):

	def makeConnection(transport):
		'''
		Notification about the WebSocket connection
		@param transport: A L{WebSocketTransport} instance wrapping a parent transport.
		@type transport: L{WebSocketTransport}
		'''

	def closeReceived(opcode, statusCode, statusMessage):
		'''
		Callback when a status is received
		:param opcode: WS opcode received (defined in framing.py)
		:param statusCode: Status code received (defined in framing.py)
		:param statusMessage: Status message received.
		'''

	def frameReceived(opcode, data, fin):
		'''
		Callback when a frame is received
		:param opcode: Websocket opcode
		:param data: The data received
		:param fin: Whether the remote endpoint is done sending this frame.
		'''

class WebSocketTransport(object):
	def __init__(self, transport):
		self.disconnecting = False
		self.parentTransport = transport


	def sendFrame(self, opcode, data):
		packet = buildFrame(opcode, data)
		self.parentTransport.write(packet)


	def loseConnection(self, code=NORMAL, reason=""):
		if not self.disconnecting:
			data = packUShort(code) + reason.encode('utf8')
			frame = buildFrame(CLOSE, data, fin=True)
			self.parentTransport.write(frame)
			self.disconnecting = True
			self.parentTransport.loseConnection()

	# for getPeer() etc
	def __getattr__(self, item):
		return getattr(self.parentTransport, item)



class WebSocketProtocol(Protocol):
	def __init__(self, receiver):
		'''
		@param receiver Object to callback when frames/statuses are received
		@type receiver L{IWebSocketFrameReceiver}
		:return:
		'''
		self.receiver = receiver
		self._buffer = b''
		self.pingDeferred = Deferred()
		self.shit = 0

	def connectionMade(self):
		peer = self.transport.getPeer()
		log.msg(format="Opening connection with %(peer)s", peer=peer)
		self.receiver.makeConnection(WebSocketTransport(self.transport))


	def _parseBuffer(self):

		for opcode, data, (statusCode, statusMessage), fin in parseFrames(self._buffer):
			if opcode == CLOSE:
				# Close the connection
				self.receiver.closeReceived(statusCode, statusMessage)
				self.transport.loseConnection()
				return
			elif opcode == PONG:
				pass # TODO - add ping functionality onto the protocol
			elif opcode == PING:
				self.transport.write(buildFrame(PONG, data))
			else:
				self.receiver.frameReceived(opcode, data)

	def dataReceived(self, data):
		self._buffer += data
		try:
			self._parseBuffer()
			self._buffer = b''
		except:
			log.err()
			self.transport.loseConnection()
try:
	from orbit.encoding import packByte, packUShort, packULong, Reader, ReadException
except ImportError:
	from orbit.pyencoding import packByte, packUShort, packULong, Reader, ReadException
from hashlib import sha1

WS_GUID = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

ctypedef unsigned char opcode_t

# Frame Opcodes
CONTINUE, TEXT, BINARY, CLOSE, PING, PONG = 0, 1, 2, 8, 9, 10

ctypedef unsigned short status_t

# Status codes
NORMAL, GOING_AWAY, PROTOCOL_ERROR, UNSUPPORTED_DATA, NONE, ABNORMAL_CLOSE, INVALID_PAYLOAD = 1000, 1001, 1002, 1003, 1005, 1006, 1007
POLICY_VIOLATION, MESSAGE_TOO_BIG, MISSING_EXTENSIONS, INTERNAL_ERROR, TLS_HANDSHAKE_FAILED = 1008, 1009, 1010, 1011, 1056

cpdef bytes mask(bytes data, bytes key):
	cdef list realKey = [ord(k) for k in key]
	cdef int i
	cdef list buf = list(data)
	for i, byte in enumerate(data):
		buf[i] = chr(ord(byte) ^ realKey[i % 4])
	return b''.join(buf)

cpdef bytes buildAccept(key):
	return sha1('%s%s' % (key, WS_GUID)).digest().encode('base64').strip()

cdef inline bint is_reserved_code(unsigned char opcode):
	return 2 < opcode < 8 or opcode > 10

cdef inline bint is_control_code(unsigned char opcode):
	return opcode > 7

cpdef bytes buildFrame(int opcode=-1, bytes body=b'', bytes bMask=None, bint fin=0):
	cdef unsigned long blen = len(body)
	cdef char lengthMask
	cdef bytes header, length
	if bMask is not None:
		lengthMask = 0x80
	else:
		lengthMask = 0

	if blen > 0xffff:
		length = packByte(lengthMask | 0x7f) + packULong(blen)
	elif blen > 0x7D:
		length = packByte(lengthMask | 0x7e) + packUShort(blen)
	else:
		length = packByte(lengthMask | blen)

	cdef unsigned char headerMask
	if fin:
		headerMask = 0x80
	else:
		headerMask = 0x01
	header = packByte(headerMask | opcode)
	if bMask is not None:
		body = bMask + mask(body, bMask)
	return header + length + body

def parseFrames(bytes rawData):
	r = Reader(rawData)
	cdef unsigned long blen = len(rawData)
	cdef unsigned char header
	cdef bint fin
	cdef bint masked
	cdef bytes key
	cdef bytes data
	cdef opcode_t opcode
	cdef unsigned long length
	cdef unsigned short statusCode
	cdef str statusMessage = ''
	while True:
		statusCode = NORMAL
		statusMessage = ''
		try:
			header = r.readByte()
			fin = header & 0x80
			opcode = header & 0xf

			length = r.readByte()
			masked = length & 0x80

			length &= 0x7f

			if length == 0x7e:
				length = r.readUShort()
			elif length == 0x7f:
				length = r.readULong()

			if masked:
				key = r.readChars(4)

			data = r.data[r.index:r.index + length]
			r.advance(length)

			if masked:
				data = mask(data, key)

			if opcode == CLOSE:
				tmpr = Reader(data)
				statusCode = tmpr.readUShort()
				statusMessage = data[2:].encode('utf8')
			r.commit()
			yield opcode, data, (statusCode, statusMessage), fin
		except ReadException:
			break
		yield -1, r.data[r.index:], (NORMAL, ''), 0

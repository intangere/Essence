import socket
def IRC(client, ID):
	s = socket.socket()
	s.connect(("irc.asia", 6667))
	nick = ID[4:]
	s.send("NICK %s\r\n" % nick)
	s.send("USER %s %s %s :%s\r\n" % (nick, nick, nick, nick))
	connected = True
	while connected:
		data = s.recv(100).strip()
		client.sendUpdate(data, "NORMAL")
		if " 252 " in data:
			s.send("JOIN #iris\r\n")
			s.send("PRIVMSG #iris :Connected using websocket\r\n")
		if ".close" in data:
			s.send("QUIT Shutting off..\r\n")
			s.close()
			connected = False
		if "PING " in data:
			s.send("PONG %s\r\n" % data.split()[1])
		if "ERROR :Closing Link:" in data:
			connected = False
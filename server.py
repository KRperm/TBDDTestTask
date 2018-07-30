#!/usr/bin/env python3
import socket
import select
import datetime
import json
import pickle
import argparse
import sqlite3
import time

class Database:

	def __init__(self, dbName):
		INITSCRIPT = '''
		CREATE TABLE IF NOT EXISTS "user" ("UserId" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"UserName" TEXT NOT NULL,"UserPassword" TEXT NOT NULL);
		CREATE TABLE IF NOT EXISTS "message" ("MessageId" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"MessageTime" INTEGER NOT NULL,"MessageAuthor" INTEGER NOT NULL,"MessageContent" TEXT NOT NULL);
		CREATE UNIQUE INDEX IF NOT EXISTS "MessageIdIndex" ON "message" ("MessageId");
		CREATE UNIQUE INDEX IF NOT EXISTS "UserIdIndex" ON "user" ("UserId");
		CREATE INDEX IF NOT EXISTS "MessageAuthorIndex" ON "message" ("MessageAuthor");
		'''

		self.connection = sqlite3.connect(dbName)
		self.cursor = self.connection.cursor()
		self.cursor.executescript(INITSCRIPT)
		self.connection.commit()

	def addUser(self, name, password):
		self.cursor.execute("INSERT INTO user (UserName, UserPassword) VALUES (?, ?)", (name, password))
		self.connection.commit()

	def getUserByNameAndPass(self, name, password):
		self.cursor.execute("SELECT * FROM user WHERE UserName = ? AND UserPassword = ?", (name, password))
		return self.cursor.fetchone()

	def getUserByName(self, name):
		self.cursor.execute("SELECT * FROM user WHERE UserName = ?", (name,))
		return self.cursor.fetchone()

	def addMessage(self, author, message):
		self.cursor.execute("INSERT INTO message (MessageTime, MessageAuthor, MessageContent) VALUES (?, ?, ?)", ( int(time.time()), author, message))
		self.connection.commit()

	def getMessageFromTime(self, timeFrom, timeTo):
		self.cursor.execute("SELECT MessageTime, MessageContent, UserName FROM message INNER JOIN user ON message.MessageAuthor = user.UserId WHERE MessageTime >= ? AND MessageTime <= ? ORDER BY MessageTime ASC", (timeFrom, timeTo))
		return self.cursor.fetchall()

class User:
	def __init__(self, name, sock, addr):
		self.sock = sock
		self.addr = addr
		self.name = name
		self.id = None
		self.isInChatRoom = False
		self.isAuth = False
		print("+Client (%s, %s) connected" % addr)

	def __del__(self):
		print("-Client (%s, %s) disconnected" % self.addr)
		self.sock.close();


class ChatServer:

	def __init__(self, setup = {}):

		serverProperties = {
			"buffer": 4096, 
			"ip": "127.0.0.1", 
			"port": 50000, 
			"servername": "Server", 
			"dbname": "chat.db"
		}
		serverProperties.update(setup)

		self.userList = [];

		self.recvBuffer = serverProperties["buffer"]

		self.isConnectionRunning = True

		self.serverSocket = socket.socket()
		self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.serverSocket.bind((serverProperties["ip"], serverProperties["port"]))
		self.serverSocket.listen(10)

		self.serverName = serverProperties["servername"]

		self.db = Database(serverProperties["dbname"])

	def __del__(self):
		self.isConnectionRunning = False
		for user in self.userList:
			del user
		self.serverSocket.close()

	def getSocketsList(self):
		return [u.sock for u in self.userList] + [self.serverSocket]

	def run(self):
		print("starting server")
		while self.isConnectionRunning:
			readyToRead,readyToWrite,inError = select.select(self.getSocketsList(),[],[],0)
			for s in readyToRead:
				if s == self.serverSocket:
					sockfd, addr = self.serverSocket.accept()

					self.userList.append(User("Guest", sockfd, addr))
				else:
					data = s.recv(self.recvBuffer);
					if data:
						
						try:
							data = pickle.loads(data)
						except:
							continue

						self.parseChat(data, self.findUserBySocket(s))
					else:
						discUser = self.findUserBySocket(s)
						if(discUser.isInChatRoom):
							self.broadcast("Соединение с %s было разорвано" % discUser.name);
						self.userList.remove(discUser)
						del discUser


	def findUserBySocket(self, sock):
		for u in self.userList:
			if sock == u.sock:
				return u
		return None

	def parseChat(self, data, sender):
		#const
		ERRORNOTAUTH = 0
		ERRORALREADYAUTH = 1
		ERRORUSERNOTEXIST = 2
		ERRORUSEREXIST = 3
		ERRORNOTINCHAT = 4
		ERRORINCHAT = 5
		ERRORWRONGARGS = 6
		ERRORHISTORYNOTFOUND = 7


		SUCCESSAUTH = 0
		SUCCESSREG = 1
		SUCCESSUNAUTH = 2
		SUCCESSENTER = 3
		SUCCESSQUIT = 4
		SUCCESSGETHISTORY = 5

		if(data["action"] == "reg"):
			if sender.isInChatRoom:
				self.sendMessage({"error": ERRORINCHAT}, sender)
			elif not(data.get("name") and data.get("password")):
				self.sendMessage({"error": ERRORWRONGARGS}, sender)
			elif (self.db.getUserByName(data["name"]) != None):
				self.sendMessage({"error": ERRORUSEREXIST}, sender)
			else:
				self.db.addUser(data["name"], data["password"])
				self.sendMessage({"success": SUCCESSREG}, sender)


		elif(data["action"] == "auth"):
			if sender.isAuth:
				self.sendMessage({"error": ERRORALREADYAUTH}, sender)
			elif not(data.get("name") and data.get("password")):
				self.sendMessage({"error": ERRORWRONGARGS}, sender)
			else:
				user = self.db.getUserByNameAndPass(data["name"], data["password"])
				if(user != None):
					sender.name = user[1]
					sender.id = user[0]
					sender.isAuth = True
					self.sendMessage({"success": SUCCESSAUTH}, sender)
				else:
					self.sendMessage({"error": ERRORUSERNOTEXIST}, sender)

		elif(data["action"] == "unauth"):
			if not sender.isAuth:
				self.sendMessage({"error": ERRORNOTAUTH}, sender)
			elif sender.isInChatRoom:
				self.sendMessage({"error": ERRORINCHAT}, sender)
			else:
				self.sendMessage({"success": SUCCESSUNAUTH}, sender)
				sender.isAuth = False;

		elif(data["action"] == "enter"):
			if not sender.isAuth:
				self.sendMessage({"error": ERRORNOTAUTH}, sender)
			elif sender.isInChatRoom:
				self.sendMessage({"error": ERRORINCHAT}, sender)
			else:
				self.sendMessage({"success": SUCCESSENTER}, sender)
				self.broadcast({"newmessage": "%s подключился." % sender.name, "from": self.serverName})
				sender.isInChatRoom = True;


		elif(data["action"] == "quit"):
			if sender.isInChatRoom:
				sender.isInChatRoom = False;
				self.sendMessage({"success": SUCCESSQUIT}, sender)
				self.broadcast({"newmessage": "%s вышел из чата." % sender.name, "from": self.serverName})
			else:
				self.sendMessage({"error": ERRORNOTINCHAT}, sender)


		elif(data["action"] == "disconnect"):
			if sender.isInChatRoom:
				self.broadcast({"newmessage": "%s вышел из чата." % sender.name, "from": self.serverName})
			self.userList.remove(sender)
			del sender


		elif(data["action"] == "gethistory"):
			if not(data.get("timeFrom") and data.get("timeTo")):
				self.sendMessage({"error": ERRORWRONGARGS}, sender)
			elif sender.isInChatRoom:
				self.sendMessage({"error": ERRORINCHAT}, sender)
			else:
				hMessages = self.db.getMessageFromTime(data["timeFrom"], data["timeTo"])
				if len(hMessages) > 0:
					self.sendMessage({"success": SUCCESSGETHISTORY, "historymessages": hMessages}, sender)
				else:
					self.sendMessage({"error": ERRORHISTORYNOTFOUND}, sender)


		elif(data["action"] == "broadcast"):
			if not sender.isAuth:
				self.sendMessage({"error": ERRORNOTAUTH}, sender)
			elif not sender.isInChatRoom:
				self.sendMessage({"error": ERRORNOTINCHAT}, sender)
			else:
				self.db.addMessage(sender.id, data["message"])
				self.broadcast({"newmessage": data["message"], "from": sender.name})


	def broadcast(self, message):
		message.update({"time": int(time.time())})
		for u in self.userList:
			if u.isInChatRoom and u.isAuth:
				self.sendMessage(message, u)
				

	def sendMessage(self, message, sendto):
		try:
			messageToSend = pickle.dumps(message)
		except:
			print("Cannot encode data: %s" % message)
			return None

		try :
			sendto.sock.send(messageToSend)
		except :
			discUser = self.findUserBySocket(s)
			if(discUser.isInChatRoom):
				self.broadcast({"newmessage": "Соединение с %s было разорвано." % discUser.name, "from": self.serverName});
			self.userList.remove(discUser)
			del discUser

if __name__ == '__main__':
	setup = {}
	server = None

	try:
		with open('serverSetup.json', 'r', encoding='utf-8') as jsonData:
			setup = json.load(jsonData)
	except:
		print("no setup file")

	parser = argparse.ArgumentParser(add_help=True)
	parser.add_argument('-b', '--buffer', action='append', help='Buffer size of message that will be received', type=int)
	parser.add_argument('-i', '--ip', action='append', help='Ip Address of server')
	parser.add_argument('-p', '--port', action='append', help='Port of server', type=int)
	parser.add_argument('-n', '--servername', action='append', help='Name of server, which will shown to client')
	parser.add_argument('-d', '--dbname', action='append', help='Name for database file')

	args = vars(parser.parse_args())
	setupFromArgs = {}
	for key in args:
		if args[key]:
			setupFromArgs[key] = args[key][0]
	setup.update(setupFromArgs)

	try:
		server = ChatServer(setup)
		server.run()
	except (KeyboardInterrupt, SystemExit):
		print('shutting down the server')
		del server
	except Exception as e:
		raise e
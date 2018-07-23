import socket
import select
import sqlite3
import datetime
import json
import time

class Database:
	def __init__(self, dbName):
		self.connection = sqlite3.connect(dbName)
		self.cursor = self.connection.cursor()
		self.cursor.executescript('CREATE TABLE IF NOT EXISTS "User" ("UserId" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"UserName" TEXT NOT NULL,"UserPassword" TEXT NOT NULL);CREATE TABLE IF NOT EXISTS "message" ("MessageId" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"MessageTime" INTEGER NOT NULL,"MessageAuthor" INTEGER NOT NULL,"MessageContent" TEXT NOT NULL);')
		self.connection.commit()

	def addUser(self, name, password):
		self.cursor.execute("INSERT INTO user (UserName, UserPassword) VALUES ('{}', '{}')".format(name, password))
		self.connection.commit()

	def getUserByNameAndPass(self, name, password):
		self.cursor.execute("SELECT * FROM user WHERE UserName = '{}' AND UserPassword = '{}'".format(name, password))
		return self.cursor.fetchone()

	def getUserByName(self, name):
		self.cursor.execute("SELECT * FROM user WHERE UserName = '{}'".format(name))
		return self.cursor.fetchone()

	def addMessage(self, author, message):
		self.cursor.execute("INSERT INTO message (MessageTime, MessageAuthor, MessageContent) VALUES ({}, {}, '{}')".format( int(time.time()), author, message))
		self.connection.commit()

	def getMessageFromTime(self, timeFrom, timeTo):
		self.cursor.execute("SELECT * FROM message INNER JOIN user on message.MessageAuthor = user.UserId WHERE MessageTime >= {} AND MessageTime <= {} ORDER BY MessageTime ASC".format(timeFrom, timeTo))
		return self.cursor.fetchall()

class User:
	def __init__(self, name, sock):
		self.sock = sock
		self.name = name
		self.id = None
		self.isInChatRoom = False
		self.isAuth = False;


class ChatServer:
	"""docstring for Server"""
	def __init__(self, recvBuffer = 4096, ipAddr = "127.0.0.1", port = 50000, serverName = "Server", dbName = "chat.db"):
		#super(Server, self).__init__()
		self.userList = [];

		self.recvBuffer = recvBuffer

		serverSocket = socket.socket()
		serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		serverSocket.bind((ipAddr, port))
		serverSocket.listen(10)
		self.serverAccount = User(serverName, serverSocket)
		self.serverAccount.isInChatRoom = True
		self.serverAccount.isAuth = True

		self.userList.append(self.serverAccount)

		self.db = Database(dbName)

		self.loop()

	def getSocketsList(self):
		return [u.sock for u in self.userList]

	def loop(self):
		while True:
			socketList = self.getSocketsList();
			readyToRead,readyToWrite,inError = select.select(socketList,[],[],0)
			for s in readyToRead:
				if s == self.serverAccount.sock:
					sockfd, addr = self.serverAccount.sock.accept()

					self.userList.append(User("Guest", sockfd))
					print("Client (%s, %s) connected" % addr)
				else:
					data = s.recv(self.recvBuffer);
					if data:
						data = data.decode("utf8");
						self.parseChat(data, self.findUserBySocket(s))
					else:
						discUser = self.findUserBySocket(s)
						if(discUser.isInChatRoom):
							self.broadcast("Соединение с {} было разорвано".format(discUser.name), self.serverAccount);
						self.userList.remove(discUser)

		serverAccount.sock.close()


	def findUserBySocket(self, sock):
		for u in self.userList:
			if sock == u.sock:
				return u
		return None

	def parseChat(self, data, sender):
		if data != "":
			rawData = data[2:].replace("\r", "").replace("\n", "")
			args = rawData.split(" ")

			#L data1 data2 ...
			if (data[0] == "R"): #register // R user password
				if sender.isInChatRoom:
					self.sendMessage("Выйдите из чат группы, чтобы пройти регистрацию", sender, self.serverAccount)
				elif len(args) != 2:
					self.sendMessage("Недостаточно агрументов. Ожидаю 2", sender, self.serverAccount)
				else:
					if(self.db.getUserByName(args[0]) == None):
						self.db.addUser(args[0], args[1])
						self.sendMessage("Пользователь {} успешно зарегистрировался".format(args[0]), sender, self.serverAccount)
					else:
						self.sendMessage("Пользователь с таким именем уже существует", sender, self.serverAccount)
					
			#######
			elif (data[0] == "A"): #auth
				if len(args) != 2:
					self.sendMessage("Недостаточно агрументов. Ожидаю 2", sender, self.serverAccount)
				elif sender.isAuth:
					self.sendMessage("Уже авторизированы", sender, self.serverAccount)
				else:
					user = self.db.getUserByNameAndPass(args[0], args[1])
					if(user != None):
						sender.name = user[1]
						sender.id = user[0]
						sender.isAuth = True
						self.sendMessage("Успешно авторизовался", sender, self.serverAccount)
					else:
						self.sendMessage("Пользователя не существует или пароль введен не верно", sender, self.serverAccount)
						
			#######
			elif (data[0] == "U"): #unauth
				if sender.isInChatRoom:
					self.sendMessage("Не могу выйти из учетной записи. Выйдите из чат-группы сначала", sender, self.serverAccount)
				else:
					self.sendMessage("Вышел из учетной записи", sender, self.serverAccount)
					sender.isAuth = False;
			#######
			elif (data[0] == "E"): #enter to room
				if not sender.isAuth:
					self.sendMessage("Для входа необходима авторизация", sender, self.serverAccount)
				elif sender.isInChatRoom:
					self.sendMessage("Вы уже в чат-группе", sender, self.serverAccount)
				else:
					self.sendMessage("Вы вошли в чат-группу", sender, self.serverAccount)
					self.broadcast("{} подключился".format(sender.name), self.serverAccount)
					sender.isInChatRoom = True;
					
			#######
			elif (data[0] == "Q"): #quit from room
				if sender.isInChatRoom:
					sender.isInChatRoom = False;
					self.sendMessage("Вы вышли из чат-группы", sender, self.serverAccount)
					self.broadcast("{} вышел из чата".format(sender.name), self.serverAccount)
				else:
					self.sendMessage("Вы не находитесь в чат-группе", sender, self.serverAccount)
			#######
			elif (data[0] == "M"): #send message
				if not sender.isAuth:
					self.sendMessage("Для отправки сообщения необходима авторизация", sender, self.serverAccount)
				elif not sender.isInChatRoom:
					self.sendMessage("Войди в чат-группу", sender, self.serverAccount)
				else:
					self.db.addMessage(sender.id, rawData)
					self.broadcast(rawData, sender)
			#######
			elif (data[0] == "D"): #Disconnect
				if sender.isInChatRoom:
					self.broadcast("{} вышел из чата.".format(sender.name), self.serverAccount);
				sender.sock.close()
				self.userList.remove(sender)
			#######
			elif (data[0] == "H"): #History
				if len(args) != 2:
					self.sendMessage("Недостаточно агрументов. Ожидаю 2", sender, self.serverAccount)
				elif sender.isInChatRoom:
					self.sendMessage("Выйдите из чат-грппы, чтобы посмотреть историю сообщений", sender, self.serverAccount)
				else:
					hMessages = self.db.getMessageFromTime(args[0], args[1])
					if len(hMessages) > 0:
						self.sendMessage("=== Результат запроса ===\n" + self.composeMessages(hMessages) + "=== Конец запроса ===", sender, self.serverAccount)
					else:
						self.sendMessage("Сообщений в этот период не найдено", sender, self.serverAccount)
					


	def broadcast(self, message, sender):
		for u in self.userList:
			if u.sock != self.serverAccount.sock and u.isInChatRoom and u.isAuth:
				self.sendMessage(message, u, sender, False)
				

	def sendMessage(self, message, sendto, sendfrom, isPrivate = True):
		privateSign = ""
		if isPrivate:
			privateSign = "(Личное сообщение)"
		message = "[{}] {}{}: {}\n".format(datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S"), sendfrom.name, privateSign, message)
		message = message.encode('utf8')
		try :
			sendto.sock.send(message)
		except :
			discUser = self.findUserBySocket(s)
			if(discUser.isInChatRoom):
				self.broadcast("Соединение с {} было разорвано.".format(discUser.name), self.serverAccount);
			sendto.sock.close()
			self.userList.remove(discUser)

	def composeMessages(self, rawData):
		result = ""
		for row in rawData:
			result += "[{}] {}: {}\n".format(datetime.datetime.fromtimestamp(row[1]), row[5], row[3])
		return result

setup = None
try:
	with open('serverSetup.json', 'r', encoding='utf-8') as jsonData:
		setup = json.load(jsonData)
		ChatServer(setup.get('buffer', 4096), setup.get('ip', '127.0.0.1'), setup.get('port', 50000), setup.get('servername', 'Server'), setup.get('dbname', 'chat.db'));
except:
	print("no setup file")
	ChatServer();
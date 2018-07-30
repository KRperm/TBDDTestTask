#!/usr/bin/env python3
import socket
import select
import datetime
import json
import pickle
import argparse
import re
import sys

class ChatClient:
	def __init__(self, setup = {}):

		clientProperties = {
			"buffer": 4096, 
			"ip": "127.0.0.1", 
			"port": 50000
		}
		clientProperties.update(setup)

		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.settimeout(2)

		self.messageBuffer = ""

		self.recvBuffer = clientProperties["buffer"]

		self.socketList = [sys.stdin, self.sock]

		self.isConnectionRunning = True

		self.errorMessages = [
			"Вы должны быть авторизированы, чтобы выполнить это действие", #ERRORNOTAUTH = 0
			"Вы уже авторизированы", #ERRORALREADYAUTH = 1
			"Такого пользователя не существует или пароль введен неверно", #ERRORUSERNOTEXIST = 2
			"Такой пользователь уже существует", #ERRORUSEREXIST = 3
			"Войдите в чат-группу, чтобы выполнить это действие", #ERRORNOTINCHAT = 4
			"Выйдите из чат-группы, чтобы выполнить это действие", #ERRORINCHAT = 5
			"Неверное количество аргументов", #ERRORWRONGARGS = 6
			"Не найдено сообщений за этот период" #ERRORHISTORYNOTFOUND = 7
		]
		self.successMessages = [
			"вошел в учетную запись", #SUCCESSAUTH = 0
			"зарегестрировался", #SUCCESSREG = 1
			"вышел из учетной записи", #SUCCESSUNAUTH = 2
			"вошел в группу", #SUCCESSENTER = 3
			"вышел из группы", #SUCCESSQUIT = 4
			"История сообщений получена" #SUCCESSGETHISTORY = 5
		]

		self.helpMessage = """-----
Добро пожаловать
Введите команду
/help - Вывести это окно
/reg - Зарегистрируйтесь
/auth - Авторизируйтесь
/enter - Войти в чат-комнату
/quit - Выйти из чат-комнаты
/history - Просмотр истории сообщений
/disconn - Отключится от сервера и выйти из программы
-----"""
			 
		try :
			self.sock.connect((clientProperties["ip"], clientProperties["port"]))
			print(self.helpMessage)

			if clientProperties.get("username"):
				password = self.enterData("Введите пароль для пользователя %s" % clientProperties["username"])
				if password:
					self.sendMessage({"action": "auth", "name": clientProperties["username"], "password": password})
		except :
			print('Не могу подключится')

	def __del__(self):
		self.isConnectionRunning = False
		self.sock.close()
		print("Отключаюсь")

	def run(self):
		while self.isConnectionRunning:
			readyToRead,readyToWrite,inError = select.select(self.socketList , [], [])
			 
			for s in readyToRead:
				if s == self.sock:
					data = s.recv(self.recvBuffer)
					if data :

						try:
							data = pickle.loads(data)
						except:
							print("Сервер послал некорректные данные")
							continue

						self.parseServerMessage(data)
					else :
						print("Нет соединения с сервером")
						self.isConnectionRunning = False;
				else :
					message = sys.stdin.readline()[:-1]
					self.parseInput(message)

	def getDescriptionOfServerResponse(self, data):
		if(data.get("success") != None):
			return self.successMessages[data["success"]]
		elif(data.get("error") != None):
			return "Ошибка. " + self.errorMessages[data["error"]]
		else:
			return None


	def parseServerMessage(self, data):
		serverResponse = self.getDescriptionOfServerResponse(data)
		if serverResponse:
			print(">>> " + serverResponse)

		if(data.get("newmessage")):
			print(self.composeMessage((data["time"], data["newmessage"], data["from"])))

		if(data.get("historymessages")):
			for message in data["historymessages"]:
				print(self.composeMessage(message))

	def parseInput(self, message):
		if(message == "/help"):
			print(self.helpMessage)


		elif(message == "/reg"):
			print("Для регистрации введите свой псевдоним и пароль")
			namepass = self.enterNameAndPass();
			if(namepass):
				ObjectToSend = {"action": "reg"}
				ObjectToSend.update(namepass)
				self.sendMessage(ObjectToSend)


		elif(message == "/auth"):
			print("Для авторизации введите свой псевдоним и пароль")
			namepass = self.enterNameAndPass();
			if(namepass):
				ObjectToSend = {"action": "auth"}
				ObjectToSend.update(namepass)
				self.sendMessage(ObjectToSend)

		elif(message == "/unauth"):
			self.sendMessage({"action": "unauth"})

		elif(message == "/enter"):
			self.sendMessage({"action": "enter"})


		elif(message == "/quit"):
			self.sendMessage({"action": "quit"})


		elif(message == "/disconn"):
			self.sendMessage({"action": "disconnect"})


		elif(message == "/history"):
			print("В каком временном периоде искать сообщения?")
			date = self.enterFromTimeAndToTime();
			if(date):
				ObjectToSend = {"action": "gethistory"}
				ObjectToSend.update(date)
				self.sendMessage(ObjectToSend)


		else:
			self.sendMessage({"action": "broadcast", "message": message})

	def enterFromTimeAndToTime(self):
		timeFrom = self.enterDate("С какой даты нужно искать сообщения?")
		if(not timeFrom):
			print("Ввод данных отменен")
			return None
		timeTo = self.enterDate("До какой даты нужно искать сообщения?")
		if(not timeTo):
			print("Ввод данных отменен")
			return None
		return  {"timeFrom": int(timeFrom.timestamp()), "timeTo": int(timeTo.timestamp())}

	def enterDate(self, lable):
		while True:
			print(lable)
			print("Введите дату в формате 'гггг-мм-дд чч:мм:cc'")
			print("введите /quit чтобы отменить ввод")
			inputData = input()
			if(inputData == "/quit"):
				return None
			try:
				date = datetime.datetime.strptime(inputData, "%Y-%m-%d %H:%M:%S")
				return date
			except:
				print("Ошибка. неверно введена дата")

	def enterData(self, lable):
		while True:
			print(lable)
			print("Допустимы только буквы латинского алфавита и цифры")
			print("введите /quit чтобы отменить ввод")
			inputData = input()
			if(inputData == "/quit"):
				return None

			reResult = re.search("[a-zA-Z0-9]+", inputData)
			if(reResult and reResult.group(0) == inputData):
				return inputData
			elif(inputData == ""):
				print("Ошибка. Введена пустая строка")
			else:
				print("Ошибка. Присутствуют недопустимые символы")

	def enterNameAndPass(self):
		name = self.enterData("Введи псевдоним")
		if(not name):
			print("Ввод данных отменен")
			return None
		passwd = self.enterData("Введи пароль")
		if(not passwd):
			print("Ввод данных отменен")
			return None
		return {"name": name, "password": passwd}

	def sendMessage(self, message):
		try:
			messageToInput = pickle.dumps(message)
		except:
			print('Не могу сформировать сообщение')
			return None

		try:
			self.sock.send(messageToInput)
		except:
			print("Соединение с сервером потеряно")

	def composeMessage(self, data): # data = (time, message, username)
		return "[%s] %s: %s" % (datetime.datetime.fromtimestamp(data[0]), data[2], data[1])


if __name__ == '__main__':
	setup = {}
	client = None
	try:
		with open('clientSetup.json', 'r', encoding='utf-8') as jsonData:
			setup = json.load(jsonData)
	except:
		print("Нет файла конфигурации. Использую стандартные значения")

	parser = argparse.ArgumentParser(add_help=True)
	parser.add_argument('-b', '--buffer', action='append', help='Buffer size of message that will be received', type=int)
	parser.add_argument('-i', '--ip', action='append', help='Connect to chat server at this ip address')
	parser.add_argument('-p', '--port', action='append', help='Connect to chat server with this port', type=int)
	parser.add_argument('-u', '--username', action='append', help='Authorise under this username after program starts')

	args = vars(parser.parse_args())
	setupFromArgs = {}
	for key in args:
		if args[key]:
			setupFromArgs[key] = args[key][0]
	setup.update(setupFromArgs)

	try:
		client = ChatClient(setup)
		client.run()
	except (KeyboardInterrupt, SystemExit):
		del client
	except Exception as e:
		raise e
		
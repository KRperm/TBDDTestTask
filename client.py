import sys
import socket
import select
import re
import json
import datetime

class Client:
	def __init__(self, recvBuffer = 4096, ipAddr = "127.0.0.1", port = 50000):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.settimeout(2)

		self.messageBuffer = ""

		self.recvBuffer = recvBuffer

		self.socketList = [sys.stdin, self.sock]
			 
		try :
			self.sock.connect((ipAddr, port))
		except :
			print('Не могу подключится')
			sys.exit()

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
-----\n"""

		sys.stdout.write(self.helpMessage);
		sys.stdout.flush()
		self.loop()

	def loop(self):
		while 1:
			readyToRead,readyToWrite,inError = select.select(self.socketList , [], [])
			 
			for s in readyToRead:
				if s == self.sock:
					data = s.recv(self.recvBuffer)
					if data :
						data = data.decode("utf8")
						sys.stdout.write(data)
						sys.stdout.flush()	
					else :
						print("Нет соединения с сервером")
						sys.exit()
				
				else :
					message = sys.stdin.readline()[:-1]
					self.parseChat(message)
					sys.stdout.flush()

	def parseChat(self, message):
		if(message == "/help"):
			sys.stdout.write(self.helpMessage)
		elif(message == "/reg"):
			print("Для регистрации введите свой псевдоним и пароль") #Придумать что-то с этим
			namepass = self.enterNameAndPass();
			if(namepass):
				self.sendMessage("R " + namepass)
		elif(message == "/auth"):
			print("Для авторизации введите свой псевдоним и пароль")
			namepass = self.enterNameAndPass();
			if(namepass):
				self.sendMessage("A " + namepass)
		elif(message == "/enter"):
			self.sendMessage("E")
		elif(message == "/quit"):
			self.sendMessage("Q")
		elif(message == "/disconn"):
			self.sendMessage("D")
		elif(message == "/history"):
			print("В каком временном периоде искать сообщения?")
			date = self.enterFromTimeAndToTime();
			if(date):
				self.sendMessage("H " + date)
		else:
			self.sendMessage("M " + message)

	def enterFromTimeAndToTime(self):
		timeFrom = self.enterDate("С какой даты нужно искать сообщения?")
		if(not timeFrom):
			print("Ввод данных отменен")
			return None
		timeTo = self.enterDate("До какой даты нужно искать сообщения?")
		if(not timeTo):
			print("Ввод данных отменен")
			return None
		return "{} {}".format(int(timeFrom.timestamp()), int(timeTo.timestamp()))

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
		return "{} {}".format(name, passwd)

	def sendMessage(self, message):
		message = message.encode("utf8")
		self.sock.send(message)



setup = None
jsonData = None
try:
	jsonData = open('clientSetup.json', 'r', encoding='utf-8')
except:
	print("Нет файла конфигурации. Использую стандартные значения")
	Client()
	sys.exit()

setup = json.load(jsonData)
Client(setup.get('buffer', 4096), setup.get('ip', '127.0.0.1'), setup.get('port', 50000))
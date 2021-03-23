#!/usr/bin/env python3
import argparse
import asyncio

import klib
import re
import sys


def nameOrID():
	while "the answer is invalid":
		reply = str(input("quizName or quizID? [n/i] > ")).lower().strip()
		if reply[:1] == 'n':
			return True
		if reply[:1] == 'i':
			return False


def checkID(qID):
	res = re.search(r"(([a-zA-Z0-9]){8}(-([a-zA-Z0-9]){4}){3}-([a-zA-Z0-9]){12})", qID)
	if not res:
		print('Invalid UUID. It must take the form x8-x4-x4-x4-x12, where x8 means 8 alphanumeric characters')
		exit()
	return res.group(1)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('-s', "--search",
	                    help="Search for a quiz without joining a Kahoot. Cancels nick and pin options.",
	                    action="store_true")
	parser.add_argument('-d', "--debug", help="Output go brrrrrrrrrrrrr", action="store_true")
	parser.add_argument('-e', "--email", help="The email used to login to create.kahoot.it")
	parser.add_argument('-a', "--password", help="The corresponding password used to login to create.kahoot.it")
	parser.add_argument('-n', "--nick", help="The nickname to join the Kahoot with")
	parser.add_argument('-p', "--pin", help="The game pin")
	parser.add_argument('-q', "--quizName", help="The quiz's name")
	parser.add_argument('-i', "--quizID", help="The quiz's ID")
	parser.add_argument('-m', "--maxCount", help="How many quizzes to look for when searching by name")
	args = parser.parse_args()
	email = args.email
	password = args.password
	nickname = args.nick
	pin = args.pin
	searchOnly = args.search
	quizID = args.quizID
	quizName = args.quizName
	maxCount = args.maxCount
	debug = args.debug

	try:
		if debug:
			print("In debug mode: output will go brrrrrrrrrrrr")
		else:
			sys.tracebacklimit = 0
		if searchOnly:
			print("In searchOnly mode: kbot will not join a Kahoot")
			if quizID:
				user = klib.Kahoot(quizID=checkID(quizID), DEBUG=debug)
			elif quizName:
				if email and password:
					user = klib.Kahoot(quizName=quizName, maxCount=maxCount, DEBUG=debug)
				else:
					print('Authentication required when searching for quizzes by name')
					exit()
			else:
				if email and password:
					if nameOrID():
						user = klib.Kahoot(quizName=input('quizName > '), maxCount=maxCount, DEBUG=debug)
					else:
						user = klib.Kahoot(quizID=checkID(input('quizID > ')), DEBUG=debug)
				else:
					user = klib.Kahoot(quizID=checkID(input('quizID > ')), DEBUG=debug)
		else:
			if not nickname:
				nickname = input('name > ')
			if not pin:
				pin = input('pin > ')
			if quizID:
				user = klib.Kahoot(pin=pin, nickname=nickname, quizID=checkID(quizID), DEBUG=debug)
			elif quizName:
				if email and password:
					user = klib.Kahoot(pin=pin, nickname=nickname, quizName=quizName, maxCount=maxCount, DEBUG=debug)
				else:
					print('Authentication required when searching for quizzes by name')
					exit()
			else:
				if email and password:
					if nameOrID():
						user = klib.Kahoot(pin=pin, nickname=nickname, quizName=input('quizName > '), maxCount=maxCount,
						                   DEBUG=debug)
					else:
						user = klib.Kahoot(pin=pin, nickname=nickname, quizID=checkID(input('quizID > ')), DEBUG=debug)
				else:
					user = klib.Kahoot(pin=pin, nickname=nickname, quizID=checkID(input('quizID > ')), DEBUG=debug)
		if email and password and user:
			user.authenticate(email, password)
		if searchOnly:
			user.search()
		else:
			user.checkPin()
			user.startGame()
	except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
		print("\nBYE!")
		exit()

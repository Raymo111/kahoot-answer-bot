import requests
import json
import time
import re
import base64
import os

try:
    import aiocometd
    from py_mini_racer import py_mini_racer
    import requests
except ModuleNotFoundError:
    if "y" in input("Install dependencies? [y/N] > ").lower():
        os.system('python3 -m pip install -r requirements.txt')

import asyncio
import urllib.parse
from difflib import SequenceMatcher


class Kahoot:
    def __init__(self, pin, username):
        self.pin = pin
        self.username = username
        self.client = requests.session()
        self.captchaToken = "KAHOOT_TOKEN_eyJ2ZXJzaW9uIjoiIn0="
        # This will work until they add the version to code. https://repl.it/repls/WholeCrimsonFlashdrives
        self.authToken = None
        self.answers = None
        self.loadCodes()

    def _check_auth(f):
        def wrapper(self, *args, **kwargs):
            if not self.authToken:
                raise KahootError('You must be authenticated to use this method.')
            return f(self, *args, **kwargs)
        return wrapper

    def authenticate(self, email, password):
        url = 'https://create.kahoot.it/rest/authenticate'
        data = {'username': email, 'password': password, 'grant_type': 'password'}
        response = self.client.post(url, json=data, headers={'Content-Type': 'application/json', "x-kahoot-login-gate": "enabled"})
        if response.status_code == 401:
            raise KahootError("Invalid Email or Password.")
        elif response.status_code == 200:
            print('AUTHENTICATED')
            self.authToken = response.json()["access_token"]
        else:
            raise KahootError('Unknown login issue')

    def startGame(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._play())

    async def _play(self):
        url = f'wss://play.kahoot.it/cometd/{self.pin}/{self.sessionID}'
        async with aiocometd.Client(url, ssl=False) as client:
            self.socket = client
            await client.subscribe("/service/controller")
            await client.subscribe("/service/player")
            await client.subscribe("/service/status")
            await client.publish('/service/controller',
                                 {"host": "kahoot.it", "gameid": self.pin, "captchaToken": self.captchaToken, "name": self.username, "type": "login"})
            colors = {0: "RED", 1: "BLUE", 2: "YELLOW", 3: "GREEN"}
            offset = 0
            async for rawMessage in client:
                message = rawMessage['data']
                if 'error' in message:
                    raise KahootError(message['description'])
                if 'id' in message:
                    data = json.loads(message['content'])
                    kind = ''
                    if message['id'] in self.lookup:
                        kind = self.lookup[message['id']]

                    if kind == 'START_QUIZ':
                        quizName = data['quizName']
                        quizAnswers = data['quizQuestionAnswers']
                        self.answers = await self.findAnswers(name=quizName, exceptedAnswers=quizAnswers)
                        print(f'ANSWERS RECEIVED')
                    elif kind == 'START_QUESTION':
                        print('------', data['questionIndex']+1, '------')
                        if data['gameBlockType'] != 'quiz':
                            pass
                        elif self.answers:
                            correct = self.answers[data['questionIndex'] + offset]['index']
                            print(f'SELECTED {colors[correct]}')
                            await self.sendAnswer(correct)
                        else:
                            print('SELECTED FALLBACK')
                            await self.sendAnswer(1)
                    elif kind == 'TIME_UP':
                        # print('DID NOT ANSWER IN TIME, SKIPPING TO NEXT ANSWER')
                        # offset += 1
                        pass
                    elif kind == 'RESET_CONTROLLER' or kind == 'GAME_OVER':
                        await client.close()
                        exit()
                    print(kind.replace('_', ' '))

    async def sendAnswer(self, choice):
        choiceInfo = json.dumps({"choice": choice, "meta": {"lag": 0, "device": {"userAgent": "kbot", "screen": {"width": 1920, "height": 1080}}}})
        await self.socket.publish("/service/controller",
                                  {"content": choiceInfo,
                                   "gameid": self.pin,
                                   "host": "kahoot.it",
                                   "type": "message",
                                   "id": 45})

    @_check_auth
    async def searchQuiz(self, name, exceptedAnswers=None, maxCount=20):
        name = self._remove_emojis(name.replace("\\'", "'"))
        url = 'https://create.kahoot.it/rest/kahoots/'
        params = {'query': name, 'cursor': 0, 'limit': maxCount, 'topics': '', 'grades': '', 'orderBy': 'relevance', 'searchCluster': 1, 'includeExtendedCounters': False}
        resp = self.client.get(url, params=params, headers={'Authorization': f'Bearer {self.authToken}'})
        if resp.status_code != 200:
            raise KahootError("Something went wrong searching quizzes.")
        quizzes = resp.json()['entities']
        for quiz in quizzes:
            title = quiz['card']['title']
            if title == name:
                url = f'https://create.kahoot.it/rest/kahoots/{quiz["card"]["uuid"]}'
                resp = self.client.get(url, headers={'Authorization': f'Bearer {self.authToken}'})
                if resp.status_code == 400:
                    raise KahootError("Invalid UUID.")
                if resp.status_code != 200:
                    raise KahootError("Something went wrong finding answers.")
                if exceptedAnswers:
                    if quiz['card']['number_of_questions'] == len(exceptedAnswers):
                        isCorrectQuiz = True
                        for q_index, question in enumerate(resp.json()['questions']):
                            if len(question['choices']) != exceptedAnswers[q_index]:
                                isCorrectQuiz = False
                                break
                        if isCorrectQuiz:
                            return resp.json()
                else:
                    return resp.json()

        # Otherwise Panic
        raise KahootError("No quiz found. (private?)")

    @staticmethod
    def _remove_emojis(text):
        # https://stackoverflow.com/questions/33404752/removing-emojis-from-a-string-in-python/33417311
        emoji_pattern = re.compile("["
                                   u"\U0001F600-\U0001F64F"  # emoticons
                                   u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                   u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                   u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                   "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    @staticmethod
    def _similar(a, b):
        return SequenceMatcher(None, a, b).ratio()

    @_check_auth
    async def findAnswers(self, name, exceptedAnswers=None):
        quizProperties = await self.searchQuiz(name, exceptedAnswers)

        answers = []
        for question in quizProperties['questions']:
            foundAnswer = False
            if question['type'] != 'quiz':
                answers.append({'NOT A': 'QUESTION'})
                continue
            for i, choice in enumerate(question['choices']):
                if choice['correct'] and not foundAnswer:
                    foundAnswer = True
                    answers.append({'question': question['question'], 'index': i, 'answer': choice['answer']})
        return answers

    def checkPin(self):
        assert type(self.pin) == str
        currentTime = int(time.time())
        url = f"https://play.kahoot.it/reserve/session/{self.pin}/?{currentTime}"
        resp = self.client.get(url)
        if resp.status_code != 200:
            raise KahootError(f"Pin {self.pin} does not exist.")
        self.sessionToken = resp.headers['x-kahoot-session-token']
        self.sessionID = self.solveChallenge(resp.json()["challenge"])

    def solveChallenge(self, text):
        # Rebuilt Javascript so engine can solve it
        text = text.replace('\t', '', -1).encode('ascii', 'ignore').decode('utf-8')
        text = re.split("{|}|;", text)
        replaceFunction = "return message.replace(/./g, function(char, position) {"
        rebuilt = [text[1] + "{", text[2] + ";", replaceFunction, text[7] + ";})};", text[0]]

        jsEngine = py_mini_racer.MiniRacer()
        solution = jsEngine.eval("".join(rebuilt))
        return self._shiftBits(solution)

    def _shiftBits(self, solution):
        decodedToken = base64.b64decode(self.sessionToken).decode('utf-8', 'strict')
        solChars = [ord(s) for s in solution]
        sessChars = [ord(s) for s in decodedToken]
        return "".join([chr(sessChars[i] ^ solChars[i % len(solChars)]) for i in range(len(sessChars))])

    def loadCodes(self):
        self.lookup = {
            1: "GET_READY",
            2: "START_QUESTION",
            3: "GAME_OVER",
            4: "TIME_UP",
            5: "PLAY_AGAIN",
            6: "ANSWER_SELECTED",
            7: "ANSWER_RESPONSE",
            8: "REVEAL_ANSWER",
            9: "START_QUIZ",
            10: "RESET_CONTROLLER",
            11: "SUBMIT_FEEDBACK",
            12: "FEEDBACK",
            13: "REVEAL_RANKING",
            14: "USERNAME_ACCEPTED",
            15: "USERNAME_REJECTED",
            16: "REQUEST_RECOVERY_DATA_FROM_PLAYER",
            17: "SEND_RECOVERY_DATA_TO_CONTROLLER",
            18: "JOIN_TEAM_MEMBERS",
            19: "JOIN_TEAM_MEMBERS_RESPONSE",
            20: "START_TEAM_TALK",
            21: "SKIP_TEAM_TALK",
            31: "IFRAME_CONTROLLER_EVENT",
            32: "SERVER_IFRAME_EVENT",
            40: "STORY_BLOCK_GET_READY",
            41: "REACTION_SELECTED",
            42: "REACTION_RESPONSE",
            43: "GAME_BLOCK_START",
            44: "GAME_BLOCK_END",
            45: "GAME_BLOCK_ANSWER",
            50: "SUBMIT_TWO_FACTOR",
            51: "TWO_FACTOR_AUTH_INCORRECT",
            52: "TWO_FACTOR_AUTH_CORRECT",
            53: "RESET_TWO_FACTOR_AUTH"
        }


class KahootError(Exception):
    pass

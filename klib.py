import requests
import json
from py_mini_racer import py_mini_racer # run JS
import re
import base64
import aiocometd # websocket
import asyncio
import urllib.parse

class Kahoot:
    def __init__(self, pin, username):
        self.pin = pin
        self.username = username
        self.client = requests.session()
        self.captchaToken = "KAHOOT_TOKEN_eyJ2ZXJzaW9uIjoiIn0="  # This will work until they add the version to code. https://repl.it/repls/WholeCrimsonFlashdrives
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
        async with aiocometd.Client(url) as client:
            self.socket = client
            await client.subscribe("/service/controller")
            await client.subscribe("/service/player")
            await client.subscribe("/service/status")
            await client.publish('/service/controller', 
            {"host": "kahoot.it", "gameid": self.pin, "captchaToken": self.captchaToken, "name": name, "type": "login"})
            nonQuizQuestions = 0
            colors = {0: "RED", 1: "BLUE", 2:"YELLOW", 3:"GREEN"}
            async for rawMessage in client:
                message = rawMessage['data']
                if 'error' in message:
                    raise KahootError(message['description'])
                if 'id' in message:
                    data = json.loads(message['content'])
                    kind = self.lookup[message['id']]
                    if kind == 'START_QUIZ':
                        quizName = data['quizName']
                        self.answers = await self.findAnswers(name=quizName)
                        print(f'ANSWERS RECEIVED')
                    elif kind == 'START_QUESTION':
                        print('------',data['questionIndex']+1,'------')
                        if data['gameBlockType'] != 'quiz':
                            pass
                        elif self.answers:
                            correct = self.answers[data['questionIndex']]['index']
                            print(f'SELECTED {colors[correct]}')
                            await self.sendAnswer(correct)
                        else:
                            print('SELECTED FALLBACK')
                            await self.sendAnswer(1)
                    elif kind == 'TIME_UP':
                        pass
                    elif kind == 'RESET_CONTROLLER' or kind == 'GAME_OVER':
                        await client.close()
                        exit()
                    print(kind)

    async def sendAnswer(self, choice):
        choiceInfo = json.dumps({"choice": choice, "meta": {"lag": 0, "device": {"userAgent": "kbot", "screen": {"width": 1920, "height": 1080}}}})
        await self.socket.publish("/service/controller", 
            {"content": choiceInfo,
            "gameid": self.pin,
            "host": "kahoot.it",
            "type": "message",
            "id": 45}
            )

    @_check_auth
    async def searchQuiz(self, name, maxCount=5):
        name = name.replace("\\'","'")
        url = 'https://create.kahoot.it/rest/kahoots/'
        params = {'query': name, 'cursor': 0, 'limit': maxCount, 'topics': '', 'grades': '', 'orderBy': 'relevence', 'searchCluster': 1, 'includeExtendedCounters': False}
        resp = self.client.get(url, params=params, headers={'Authorization': f'Bearer {self.authToken}'})
        if resp.status_code != 200:
            raise KahootError("Something went wrong searching quizzes.")
        quizzes = resp.json()['entities']
        for quiz in quizzes:
            if quiz['card']['title'] == name:
                return quiz['card']['uuid']
        raise KahootError("No quiz found. (private?)")

    @_check_auth
    async def findAnswers(self, quizID=None, name=None):
        if not quizID and name:
            quizID = await self.searchQuiz(name)
        url = f'https://create.kahoot.it/rest/kahoots/{quizID}'
        
        resp = self.client.get(url, headers={'Authorization': f'Bearer {self.authToken}'})
        if resp.status_code == 400:
            raise KahootError("Invalid UUID.")
        if resp.status_code != 200:
            raise KahootError("Something went wrong finding answers.")
        answers = []
        for question in resp.json()['questions']:
            foundAnswer = False
            if question['type'] != 'quiz':
                answers.append({'NOT A':'QUESTION'})
            else:
                for i in range(question['numberOfAnswers']):
                    if question['choices'][i]['correct'] and not foundAnswer:
                        foundAnswer = True
                        answers.append({'question': question['question'], 'index': i, 'answer': question['choices'][i]['answer']})
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
        text = re.split("{|}|;", text)
        replaceFunction = "return message.replace(/./g, function(char, position) {"
        rebuilt = [text[1] + "{", text[2] + ";", replaceFunction, text[9] + ";})};", text[0]]
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


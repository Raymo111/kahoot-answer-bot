import requests
import json
import time
import re
import base64
import os

try:
    import aiocometd
    import requests
except ModuleNotFoundError:
    if "y" in input("Install dependencies? [y/N] > ").lower():
        os.system('python3 -m pip install -r requirements.txt')

import asyncio
import urllib.parse
from difflib import SequenceMatcher
from pprint import pprint

class Kahoot:
    def __init__(self, pin, username):
        self.pin = pin
        self.username = username
        self.client = requests.session()
        self.captchaToken = "KAHOOT_TOKEN_eyJ2ZXJzaW9uIjoiIn0="
        # This will work until they add the version to code. https://repl.it/repls/WholeCrimsonFlashdrives
        self.authToken = None
        self.answers = None
        self._session_id = None
        self.random_question = False
        self.random_answer = False
        self.device_info = {"device": {"userAgent": "kbot", "screen": {"width": 1920, "height": 1080}}}
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
    async def join_game(self):

        await client.publish('/service/controller')
    async def _send(self, socket, content, c_type, params={}):
        payload = {
            'content': content,
            'gameid': self.pin,
            'host': 'kahoot.it',
            'type': c_type,
            **params
        }
        try:
            await socket.publish('/service/controller', payload)
        except asyncio.TimeoutError:
            pass
    @property
    def session_id(self):
        if not self._session_id:
            self._session_id = self.get_session_id()
        return self._session_id
    async def _play(self):
        url = f'wss://play.kahoot.it/cometd/{self.pin}/{self.session_id}'
        # pprint(url)
        colors = {0: "RED", 1: "BLUE", 2: "YELLOW", 3: "GREEN"}
        reverse_colors = {'r': 0, 'b': 1, 'y': 2, 'g': 3}
        correct_question_num = None
        async with aiocometd.Client(url, ssl=False) as socket:
            await socket.subscribe('/service/controller')
            await socket.subscribe("/service/status")
            await socket.subscribe("/service/player")
            await self._send(socket, '', 'login', {'name': self.username})
            async for rawMessage in socket:
                message = rawMessage['data']
                if message.get('error'):
                    raise KahootError(f"{message['error']}:{message['description']}")
                if message.get('id') is None:
                    continue
                kind = self.lookup[message['id']]
                message['id'] = kind
                data = json.loads(message['content'])
                if kind == 'START_QUIZ':
                    quizName = data.get('quizName', data.get('quizTitle'))# data['quizName']
                    quizAnswers = data['quizQuestionAnswers']
                    self.answers = await self.findAnswers(quizName, quizAnswers)
                    print(f'ANSWERS RECEIVED')
                elif kind == 'GET_READY' and self.random_question:
                    assert self.answers is not None
                    valid_answers = list(filter(lambda x: x['questionIndex'] >= 0, self.answers))
                    for question in self.answers:
                        if question['questionIndex'] >= 0:
                            correct_question_num = question['questionIndex']
                            print(f"{question['questionIndex']} - {question['question']}")
                        if len(valid_answers) > 1:
                            correct_question_num = int(input('Correct # > '))
                    self.answers[correct_question_num]['questionIndex'] = -1

                elif kind == 'START_QUESTION':
                    assert self.answers is not None
                    if not self.random_question:
                        correct_question_num = data['questionIndex']
                    if data['gameBlockType'] == 'quiz' or self.random_question:
                        correct = self.answers[correct_question_num]
                        if self.random_answer:
                            while True:
                                correct_color = input(f'Which color is {correct["answer"]}?\n[R/Y/G/B] > ').lower()[0]
                                if reverse_colors.get(correct_color) is not None:
                                    correct_index = reverse_colors[correct_color]
                                    break
                        else:
                            correct_index = correct.get('answerIndex', 0)
                        print(f'SELECTED {colors[correct_index]}')
                        choiceInfo = json.dumps({"type": "quiz", "choice": correct_index, "meta": {"lag": 5000}})
                        await self._send(socket, choiceInfo, 'message', params={'id':45})
                    else:
                        print('Not a quiz question or no answers.')
                elif kind == 'TIME_UP':
                    pass
                    # print(f'DID NOT ANSWER IN TIME ON QUESTION {data["questionNumber"]}')
                elif kind == 'RESET_CONTROLLER' or kind == 'GAME_OVER':
                    break
            try:
                await socket.close()
                exit()
            except asyncio.CancelledError:
                exit()

    async def sendAnswer(self, socket, choice):
        choiceInfo = json.dumps({"type": "quiz", "choice": choice, "meta": {"lag": 0}})
        await self._send(socket, choiceInfo, 'message', params={'id':45})

    @_check_auth
    async def searchQuiz(self, name, exceptedAnswers, maxCount=20):
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

    @_check_auth
    async def findAnswers(self, name, exceptedAnswers):
        quizProperties = await self.searchQuiz(name, exceptedAnswers)
        answers = []
        for j, question in enumerate(quizProperties['questions']):
            foundAnswer = False
            if question['type'] != 'quiz':
                answers.append({'NOT A': 'QUESTION'})
                continue
            for i, choice in enumerate(question['choices']):
                if choice['correct'] and not foundAnswer:
                    foundAnswer = True
                    answers.append({'question': question['question'], 'questionIndex': j, 'answerIndex': i, 'answer': choice['answer']})
        return answers

    def get_session_id(self):
        currentTime = int(time.time())
        url = f"https://play.kahoot.it/reserve/session/{self.pin}/?{currentTime}"
        resp = self.client.get(url)
        if resp.status_code != 200:
            raise KahootError(f"Pin {self.pin} does not exist.")
        token = resp.headers['x-kahoot-session-token']
        challenge_bits = self._solveChallenge(resp.json()['challenge'])
        return self._shiftBits(challenge_bits, token)

    def _solveChallenge(self, text):
        solution_regex = re.compile(r'\'(.*)\'.*offset\s=(.*?);.*%\s(\d+)\)\s\+\s(\d+)\)')
        parts = re.search(solution_regex, text)
        s, offset, mod, add = parts.groups()
        offset = eval(offset.replace('\t','').encode('ascii', 'ignore'))
        built = ''
        for i, char in enumerate(s):
            built += chr((ord(char) * i + offset) % int(mod) + int(add))
        return built

    def _shiftBits(self, solution, session_token):
        decodedToken = base64.b64decode(session_token).decode('utf-8', 'strict')
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

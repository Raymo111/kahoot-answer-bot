# Kahoot Answer Bot
A bot that takes the name or ID of a kahoot and gets a perfect score... with the username of your choosing.

*This project was started by [reteps](https://github.com/reteps/kbot) but is has been broken for quite a while, so I forked it and made it work.*

## Features
- Search by quiz name (requires login) or ID
- 2FA compatible
- 

## Installation
- [ ] Optional: Make a Kahoot Account if you don't have the Kahoot's ID and want to search for a Kahoot by name
- [ ] Install Python3
  - On Windows, visit https://www.python.org/downloads/windows/
  - On MacOS, Install [Homebrew](https://brew.sh/), then install Python.
    - `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`
    - `brew install python`
  - You probably have (or know how to install) python if you're on Linux. If not, good luck.
- [ ] Download and unzip or clone this repo
  - https://github.com/Raymo111/kahoot-answer-bot/archive/master.zip
  - `git clone https://github.com/Raymo111/kahoot-answer-bot.git`
- [ ] Install Dependencies
  - `python3 -m pip install -r requirements.txt`

## Usage
```
python3 kbot [options]
```
```
-e, --email
The email used to login to create.kahoot.it

-a, --password
The corresponding password used to login to create.kahoot.it

-n, --name
The nickname to join the Kahoot with

-p, --pin
The game pin

-q, --quizName
The quiz's name

-i, --quizID
The quiz's ID

-d, --debug
Output go brrrrrrrrrrrrr
```

## Caveats
The program intercepts and pretends to be a kahoot client. After receiving quiz name from host, looks up answers for quiz and uses them.
Does not work when:
- Kahoot is private
- Answers are randomized
- Questions are randomized

This is because this program uses the original question order and answer order, so if these are randomized the wrong answer will be clicked.

## Contributors
* [Raymo111](https://github.com/Raymo111) - Fixing it
* [reteps](https://github.com/reteps) - Main programming
* [idiidk](https://github.com/idiidk) - For the challenge decoding

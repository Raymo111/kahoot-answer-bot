# Kahoot Answer Bot
A bot that takes the name or ID of a kahoot and gets a perfect score with the nickname of your choosing.

*This project was started by [reteps](https://github.com/reteps/kbot) but is has been broken for quite a while, so I forked it and made it work.*

## Features
The program intercepts and pretends to be a kahoot client. After receiving quiz name from host, looks up answers for quiz and uses them.
- Search by quiz name (requires login) or ID
- 2FA compatible

## Installation
- [ ] Optional: Make a Kahoot Account if you don't have the Kahoot's ID and want to search for a Kahoot by name
- [ ] Install Python3
	
  On Windows visit `https://www.python.org/downloads/windows/`
	- Click latest Python 3 release
	- Scroll down to the bottom to the section titled "Files"
	- Click the Windows Installer (64-bit) link to download the ".exe"
	- In File Explorer right click the file and click "Run as Administrator"
	- Check the boxes "Install launcher for all users (recommended)" and "Install Python 3.X to path"
	
	On macOS 11+ (Intel) and macOS 11+ (Apple Sillicon) visit "`https://www.python.org/downloads/macos/`"
	- Click latest Python 3 release
	- Scroll down to the bottom to the section titled "Files"
	- Click the macOS 64-bit universal2 installer link to download the ".pkg"
	- Run the downloaded ".pkg"
	
    On Debian GNU/Linux 11+ based distros:
    - `sudo apt install python3 python3-pip`

   On Arch Linux based distros run:
	- `sudo pacman -S python python-pip`

   On other Linux based distros install python3 (python) and python3-pip (python-pip) from your package manager
   
- [ ] Download and unzip or clone this repo
	- https://github.com/Raymo111/kahoot-answer-bot/archive/master.zip
	- `git clone https://github.com/Raymo111/kahoot-answer-bot.git`
- [ ] Install Dependencies
	- `python3 -m pip install -r requirements.txt`

## Usage
Open a terminal (Command Prompt on Windows) and navigate to the directory (folder) containing kbot. Then use the following command, replacing `[options]` with any options you want to use (listed below).
```
python3 kbot [options]
```
```
-e, --email
The email used to login to create.kahoot.it

-a, --password
The corresponding password used to login to create.kahoot.it

-n, --nick
The nickname to join the Kahoot with

-p, --pin
The game pin

-s --search
Search for a quiz without joining a Kahoot. Cancels nick and pin options.

-q, --quizName
The quiz's name

-i, --quizID
The quiz's ID

-d, --debug
Output go brrrrrrrrrrrrr
```

## Caveats
Does not work when:
- Kahoot is private
- Answers are randomized
- Questions are randomized

This is because this program uses the original question order and answer order, so if these are randomized the wrong answer will be clicked.

## Contributors
* [Raymo111](https://github.com/Raymo111) - Fixing it, adding 2FA and search by ID
* [reteps](https://github.com/reteps) - Main programming
* [idiidk](https://github.com/idiidk) - For the challenge decoding

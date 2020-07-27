# Kahoot Answer Bot
A bot that takes the name or ID of a kahoot and gets a perfect score... with the username of your choosing.

## Getting Started

- [ ] Make Kahoot Account
- [ ] Install Python3
  - On MacOS, Install [Homebrew](https://brew.sh/), then install Python.
    - `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`
    - `brew install python`
- [ ] Clone this project
  - `git clone https://github.com/reteps/kbot.git`
- [ ] Install Dependencies
  - `python3 -m pip install -r requirements.txt`
- [ ] Run Program
  - `python3 kbot`

## Program arguments

```
python3 kbot
  --email XYZ@gmail.com 
  --password XYZ
```

Please open a pull request or issue if you would like more functionality.

## How does it work?

Intercepts and pretends to be a kahoot client. After receiving quiz name from host, looks up answers for quiz and uses them.

## Caveats

Does not work when:

+ Kahoot is private
+ Answers are randomized
+ Questions are randomized

This is because this program uses the original question order and answer order, so if these are modified the wrong answer will be clicked.
## Questions?
 + please open an issue
 
## Contributors

* [reteps](https://github.com/reteps) - Main programming
* [idiidk](https://github.com/idiidk) - For the challenge decoding

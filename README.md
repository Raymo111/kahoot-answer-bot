<img src="https://ryand.ryansdell.tk/images/kahootbotimg.png"
width=300px height=300px alt="kBot">
# The Amazing Automatic Kahoot Bot (kbot)
People have made bots and things for kahoot in the past, but this is
a new and improved edition that actually opens a browser and does
everything for you. This one actually answers the questions, unlike
some other tools we have taken some of our inspiration from.

## How does it work?
Using a browser automation system and HTML parser, the program logs in
to a custom account at [getkahoot.it](getkahoot.it), finds the quiz
you are looking for based on its quiz ID, then grabs all the answers.

After that, the program opens [kahoot.it](kahoot.it), where it signs
in using the game PIN and a custom name. As the game moves on, the
program clicks the correct answers as soon as possible. You will get
a perfect score!

## Caveats

+ The *bot* part does not work when the questions and/or answers are _randomized_. 
+ Use `kbot QUIZID` to read out the answers
+ if the kahoot is not public on _[getkahoot.it](getkahoot.it)_, this program does not work.
+ This has only been tested on MacOS.
## Dependencies and Requirements


* python3 [mac download tutorial](https://python-guide-pt-br.readthedocs.io/en/latest/starting/install3/osx/) _Generally just a `brew install python3`_

* The [Google Chrome Web
  Browser](https://www.google.com/chrome/browser/desktop/index.html)
* [selenium for Python3](https://pypi.python.org/pypi/selenium)
  _Generally just a `pip3 install selenium`_
* [Chrome
  Driver](https://sites.google.com/a/chromium.org/chromedriver/downloads)
  _Make sure the executable is in your `$PATH` somewhere_
* [BeautifulSoup4 for Python3](https://pypi.python.org/pypi/beautifulsoup4)
  _Generally just a `pip3 install bs4`_

## FAQ
 + please see the wiki.
## Contributors
* [reteps](https://github.com/reteps)
* [rydens](https://github.com/rydens)

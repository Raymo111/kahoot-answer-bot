#!/usr/bin/env python3

#-------------------------------------------------------------------------#
#written by Peter Stenger (@reteps) with support from Ryan Densmore (@rydens)
#If you use this code, please cite us / this page.
#-------------------------------------------------------------------------#
import sys, time
from bs4 import BeautifulSoup
from selenium import webdriver
speed = 0
#-------------------------------------------------------------------------#
def get_page(id, email, passwd,speed):
    driver = webdriver.Chrome()
    driver.get('https://create.kahoot.it/#quiz/' + id);
    time.sleep(0.25 + speed)
    box = driver.find_element_by_css_selector('#username-input-field__input')
    box.send_keys(email)
    box2 = driver.find_element_by_css_selector('#password-input-field__input')
    box2.send_keys(passwd)
    driver.find_element_by_css_selector('.button--cta-play').click()
    time.sleep(2 + speed)
    elem = driver.find_element_by_xpath("//*")
    stuff = elem.get_attribute("innerHTML")
    try:
        driver.find_element_by_css_selector(".create-kahoot-type-selector")
        print("Private kahoot.")
        exit()
    except Exception:
        driver.quit()
    return stuff
#-------------------------------------------------------------------------#
def start_bot(id,name,answers):
    driver = webdriver.Chrome()
    driver.get("https://kahoot.it/#/")
    time.sleep(0.25)
    box = driver.find_element_by_css_selector('#inputSession')
    box.send_keys(id)
    driver.find_element_by_css_selector('.btn-greyscale').click()
    time.sleep(1)
    box = driver.find_element_by_css_selector('#username')
    box.send_keys(name)
    driver.find_element_by_css_selector('.btn-greyscale').click()
    input("click [ENTER] to start the bot\n")
    bot_answer(driver,answers)
#-------------------------------------------------------------------------#
def bot_answer(driver,answers):
    lookuptable = {"0":".answerA", "1":".answerB","2":".answerC","3":".answerD"}
    lookup = {"0":"red","1":"blue","2":"yellow","3":"green"}
    nextQ = False
    answered = False
    for i in range(len(answers)):
        print("Question " ,i+1)
        while True:
            try:
                driver.find_element_by_css_selector(".answer-screen")
                if not answered:
                    print("Chose " + lookup[answers[i]])
                    try:
                        driver.find_element_by_css_selector(lookuptable[answers[i]]).click()
                    except Exception as e:
                        print('Question was skipped before bot could answer.')
                        break #next question
                    answered = True
            except Exception as e:
                nextQ = True
                if nextQ and answered:
                    nextQ = False
                    answered = False
                    break
            time.sleep(0.01)
    driver.quit()
#-------------------------------------------------------------------------#
def getQuestions(soup):
    questions = []
    stuff = soup.findAll("td", {"class":'question-title'})
    for qt in stuff:
        question = qt.find("div").get_text()
        questions.append(question.strip()[:-45])
    return questions
#-------------------------------------------------------------------------#
def getAnswers(soup,hascolor=True):

    questions = soup.findAll("ul", {"class":'answers-list'})
    colors = []
    answers = []
    for i, question in enumerate(questions):
        possibleanswers = question.findAll("li", {"class":"answers-list__item"})
        for possibleanswer in possibleanswers:
            if possibleanswer.find("div",{"class":"answer-label__correct-icon"}) != None:
                num = dict(possibleanswer.find("div",{"class":'answer-label'}).attrs)["class"][1][-1]
                if hascolor:
                    lookuptable = {"0":"red", "1":"blue","2":"yellow","3":"green"}
                    color = lookuptable[num]
                    answers.append(possibleanswer.get_text().strip())
                    colors.append(color)
                else:
                    colors.append(num)
                break
                #only need 1 answer, so break

    return colors, answers
#-------------------------------------------------------------------------#
def printAnswers(url,email,passwd,co,co2,co3):
    global speed
    html = get_page(url,email,passwd,speed)
    soup = BeautifulSoup(html, 'html.parser')
    questions = getQuestions(soup)
    
    if questions == []:
        speed += 1.5
        print('failed to reach page, wifi not fast enough. Retrying with delay set to {} seconds.'.format(speed))
        printAnswers(url,email,passwd,co,co2,co3)
    colors, answers = getAnswers(soup)
    for i in range(len(questions)):
        print('{}{:100s}{}  |  {}{:6s}{} |  {}{:3d}{}  |'.format(co,questions[i],co2,co,colors[i],co2,co,i+1,co2))
        print('{}{:100s}{}  |         |       |'.format(co3,answers[i],co2))
#-------------------------------------------------------------------------#
def scrape(url,email,passwd):
    global speed
    html = get_page(url,email,passwd,speed)
    soup = BeautifulSoup(html, 'html.parser')
    answers, asd = getAnswers(soup,hascolor=False)
    if answers == []:
        speed += 1.5
        print('failed to reach page, wifi not fast enough. Retrying with delay set to {} seconds.'.format(speed))
        scrape(url,email,passwd)
    return answers
#-------------------------------------------------------------------------#

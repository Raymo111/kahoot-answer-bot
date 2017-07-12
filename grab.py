#!/usr/bin/env python3

#-------------------------------------------------------------------------#
#written by Peter Stenger (@reteps) with support from Ryan Densmore (@rydens)
#If you use this code, please cite us / this page.
#-------------------------------------------------------------------------#
import sys, time, json
from urllib import error, request
#-------------------------------------------------------------------------#
def get_details(id, email, passwd):
    authparams = {'username':email,'password':passwd,'grant_type':'password'}
    stuff = json.dumps(authparams).encode()
    data = request.Request('https://create.kahoot.it/rest/authenticate',data=stuff,headers={'content-type':'application/json'})
    try:
        response = request.urlopen(data).read()
    except error.HTTPError:
        print('The email or password is invalid')
    token = json.loads(response)['access_token']
    r = request.Request("https://create.kahoot.it/rest/kahoots/{}".format(id), headers={'content-type' : 'application/json','authorization' : token})
    try:
        response2 = json.loads(request.urlopen(r).read())['questions']
    except error.HTTPError:
        print('private kahoot')
        exit()
    qanda = []
    colors = []
    lookuptable = {0:"red", 1:"blue",2:"yellow",3:"green"} 
    speed = 0
    for question in response2:
        for i, choice in enumerate(question['choices']):
            if choice['correct'] == True:
                qanda.append([question['question'],choice['answer']])
                colors.append(lookuptable[i])
                break
    return qanda, colors
#-------------------------------------------------------------------------#
def start_bot(id,name,colors,speed=0):

    from selenium import webdriver
    driver = webdriver.Chrome()
    while True:
        try:
            driver.get("https://kahoot.it/#/")
            time.sleep(0.25 + speed)
            box = driver.find_element_by_css_selector('#inputSession')
            box.send_keys(id)
            driver.find_element_by_css_selector('.btn-greyscale').click()
            time.sleep(1.25 + speed)
            box = driver.find_element_by_css_selector('#username')
            box.send_keys(name)
            driver.find_element_by_css_selector('.btn-greyscale').click()
            break
        except Exception:
            speed += 2.5
            print('Retrying bot login with delay set to {} seconds'.format(speed))
    print('connected successfully')
    print("press [1] to start the bot\npress [2] to choose a new name\npress [3] to start on a specific question\n")
    response = input(" > ")
    if response == '3': 
        question = int(input('starting question > ')) - 1
        bot_answer(driver,colors[question:],q=question)
    elif response == '2':
        driver.quit()
        name = input('New name > ')
        print('Retrying with name set to {} and delay set to {}'.format(name,speed))
        start_bot(id,name,colors,speed=speed)
    else:
        bot_answer(driver,colors)
#-------------------------------------------------------------------------#
def bot_answer(driver,colors,q=0):
    print('bot started.')
    lookuptable = {"red":".answerA", "blue":".answerB","yellow":".answerC","green":".answerD"}
    nextQ = False
    answered = False
    for i in range(len(colors)):
        print("Question " ,i+1+q)
        while True:
            try:
                driver.find_element_by_css_selector(".answer-screen")
                if not answered:
                    try:
                        driver.find_element_by_css_selector(lookuptable[colors[i]]).click()
                        print("Chose " + colors[i])
                    except Exception as e:
                        print('Question was skipped before bot could answer.')
                        time.sleep(0.5) #prevent doubles
                        answered, nextQ = False, False
                        break #next question
                        
                    answered = True
            except Exception as e:
                nextQ = True
                if nextQ and answered:
                    nextQ, answered = False, False
                    break
            time.sleep(0.01)
    driver.quit()
#-------------------------------------------------------------------------#
def printAnswers(url,email,passwd,co,co2,co3):
    qanda, colors = get_details(url,email,passwd)

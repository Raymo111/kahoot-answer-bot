#!/usr/bin/env python3 
#-------------------------------------------------------------------------#
#written by Peter Stenger (@reteps) with support from Ryan Densmore (@rydens)
#If you use this code, please cite us / this page.
#-------------------------------------------------------------------------#
import sys, time, json
import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
#-------------------------------------------------------------------------#
def waitForItem(driver, css, timeout=10):
    WebDriverWait(driver, timeout).until(expected_conditions.visibility_of_element_located((By.CSS_SELECTOR, css)))
#-------------------------------------------------------------------------#
def get_details(kahootid, email='kahootbot28@gmail.com', passwd='botkahoot28'):
    authparams = {'username':email,'password':passwd,'grant_type':'password'}
    print('[info] trying to authenticate')
    data = requests.post('https://create.kahoot.it/rest/authenticate', \
            data=json.dumps(authparams).encode(),headers={'content-type':'application/json'}).json()
    if 'error' in data:
        print('[error] could not authenticate')
        exit()
    response = requests.get('https://create.kahoot.it/rest/kahoots/{}'.format(kahootid), \
            headers={'content-type' : 'application/json','authorization' : data['access_token']}).json()
    if 'error' in response:
        print("[error] could not find kahootID (maybe it's private)")
        exit()
    qanda = {}
    color_sequence = []
    lookuptable = {0:'red', 1:'blue',2:'yellow',3:'green'}
    speed = 0
    for question in response['questions']:
        for i in range(len(question['choices'])):
            if question['choices'][i]['correct']:
                qanda[question['question']] = question['choices'][i]['answer']
                color_sequence.append(lookuptable[i])
                break
    return qanda, color_sequence
#-------------------------------------------------------------------------#
def start_bot(kahootId,name,colors):

    driver = webdriver.Chrome()
    driver.get('https://kahoot.it/#/')
    waitForItem(driver, '#inputSession')
    driver.find_element_by_css_selector('#inputSession').send_keys(kahootId)
    driver.find_element_by_css_selector('.btn-greyscale').click()
    waitForItem(driver, '#username')
    driver.find_element_by_css_selector('#username').send_keys(name)
    time.sleep(0.1)
    driver.find_element_by_css_selector('.btn-greyscale').click()
    print('''press [1] to start the bot
press [2] to choose a new name
press [3] to start on a specific question''')
    response = input(' > ')
    if response == '3':
        question = int(input('starting question > ')) - 1
        bot_answer(driver,colors[question:],q=question)
    elif response == '2':
        driver.quit()
        name = input('New name > ')
        print('[info] Restarting bot with the name {}'.format(name))
        start_bot(id,name,colors)
    else:
        bot_answer(driver,colors)
#-------------------------------------------------------------------------#
def bot_answer(driver,colors,q=0):
    print('[info] Bot started.')
    driver.switch_to.frame(driver.find_element_by_tag_name("iframe"))
    lookuptable = {'red':'.quiz-board > button:nth-of-type(1)', 'blue':'.quiz-board > button:nth-of-type(2)',\
            'yellow':'.quiz-board > button:nth-of-type(3)','green':'.quiz-board > button:nth-of-type(4)'}
    for i in range(len(colors)):
        print('[info] Question ' ,i+1+q)
        try:
            waitForItem(driver, "div#app",timeout=20)
            driver.find_element_by_css_selector(lookuptable[colors[i]]).click()
            print('[info] Chose ' + colors[i])
        except selenium.common.exceptions.TimeoutException:
            print('[error] Question was skipped before bot could answer.')
        time.sleep(1)
    driver.quit()

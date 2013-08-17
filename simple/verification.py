#!/usr/bin/env python
'''
Verification Bot
verification.py
Christopher Su
http://christophersu.net/
Checks Google Spreadsheet linked to form for new data and applies verification flair accordingly.
'''

import gspread
import praw
from praw.handlers import MultiprocessHandler
import logging
import json
import os
from time import gmtime, strftime
import AccountDetails

def loadJSON():
    try:
        rulesFile = open(os.path.join(dir, "already_added.json"), "r")
    except IOError:
        logging.exception("Error opening already_added.json.")
        killBot()

    rulesStr = rulesFile.read()
    rulesFile.close()

    try:
        already_added = json.loads(rulesStr)
    except ValueError:
        logging.exception("Error parsing already_added.json.")
        killBot()

    return already_added

def saveJSON(already_added):
    with open(os.path.join(dir, 'already_added.json'), 'w') as outfile:
        json.dump(already_added, outfile)

def main():
    logging.info("Starting bot: " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    gc = gspread.login(AccountDetails.GSPREAD_USERNAME, AccountDetails.GSPREAD_PASSWORD)
    doc = gc.open_by_key(AccountDetails.GSPREAD_SHEET).sheet1
    usernames = doc.col_values(2)
    usernames.pop(0) # remove header that just contains the question

    handler = MultiprocessHandler()
    r = praw.Reddit(user_agent='Subot 1.0', handler=handler)
    r.login(AccountDetails.REDDIT_USERNAME_I, AccountDetails.REDDIT_PASSWORD_I)
    
    flairName = 'registered' # choose which flair to apply
    subreddit = AccountDetails.SUBREDDIT
    sub = r.get_subreddit(subreddit) # and which subreddit to run in

    already_added = loadJSON()

    for user in usernames:
        if user not in already_added:
            sub.set_flair(user, '', flairName)
            already_added.append(user)
            r.send_message(user, "Registered!", "Your registration has been received. Check /r/%s now to view your flair." % subreddit)
            logging.info("Registering: %s at %s" %(user, strftime("%Y-%m-%d %H:%M:%S", gmtime())))
            saveJSON(already_added)

def killBot():
    sys.exit(1)

if __name__ == "__main__":
    dir = os.path.dirname(__file__)
    LOG_FILENAME = os.path.join(dir, 'bot.log')
    logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO)

    try:
        main()
    except SystemExit:
        logging.info("Exit called.")
    except:
        logging.exception("Uncaught exception.")

    logging.shutdown()
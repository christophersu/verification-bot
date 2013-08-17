#!/usr/bin/env python
'''
Subot Verity
bot.py
Christopher Su
Verifies users through a Google Form, applies flair, and performs moderation tasks on submissions and comments.
'''

import gspread
import praw
import logging
import json
import os
import sys
from time import gmtime, strftime
import SubotSettings

# global
r = None # reddit session
verified = [] # verified users list

def loadJSON(json_file):
    try:
        rulesFile = open(os.path.join(dir, json_file), "r")
    except IOError:
        logging.exception("Error opening %s." % json_file)
        sys.exit(1)

    rulesStr = rulesFile.read()
    rulesFile.close()

    try:
        verified_users = json.loads(rulesStr)
    except ValueError:
        logging.exception("Error parsing %s." % json_file)
        sys.exit(1)

    return verified_users

def saveJSON(variable, json_file):
    with open(os.path.join(dir, json_file), 'w') as outfile:
        json.dump(variable, outfile)

def sendMessage(to, subject, message):
	global r
	footer = "\n\n----\n\n^This ^is ^an ^automated ^response.\n[^[Mistake?]](http://www.reddit.com/message/compose/?to=%s&subject=Error%20Report)\n[^[Suggestion]](http://www.reddit.com/message/compose/?to=%s&subject=Suggestion)\n[^[FAQ]](http://www.reddit.com/r/%s/comments/1jsifd/faq/)" % SubotSettings.REDDIT_USERNAME
	r.send_message(to, subject, message + footer)

def makeComment(submission, body):
	footer = "\n\n----\n\n^This ^is ^an ^automated ^response.\n[^[Mistake?]](http://www.reddit.com/message/compose/?to=%s&subject=Error%20Report)\n[^[Suggestion]](http://www.reddit.com/message/compose/?to=%s&subject=Suggestion)\n[^[FAQ]](http://www.reddit.com/r/%s/comments/1jsifd/faq/)" % SubotSettings.REDDIT_USERNAME
	submission.add_comment(body + footer)

def verifyUsers(subreddit):
    global r
    logging.info("Starting bot: " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    gc = gspread.login(SubotSettings.GSPREAD_USERNAME, SubotSettings.GSPREAD_PASSWORD)
    doc = gc.open_by_key(SubotSettings.GSPREAD_SHEET).sheet1

    # get data from two columns
    approvals = doc.col_values(1)
    approvals.pop(0) # remove header that just contains the question
    usernames = doc.col_values(3)
    usernames.pop(0)

    # convert y to True and n to False
    for index, item in enumerate(approvals):
        if item == 'y':
            approvals[index] = True
        elif item == 'n':
            approvals[index] = False

    dictionary = dict(zip(usernames, approvals)) # usernames as keys, booleans as values
    
    flairName = 'verified' # choose which flair to apply
    sub = r.get_subreddit(subreddit) # and which subreddit to run in

    verified = loadJSON(SubotSettings.VERIFIED_JSON)
    checked_users = loadJSON(SubotSettings.CHECKED_JSON)

    for user, approval in dictionary.iteritems():
        if approval:
            if user not in checked_users: # could change checked_users to verified to allow for 'second chances' (getting approved after being rejected first). note that this will require more work after verified_users is switched into dictionary format
                # which row is this user in the spreadsheet?
                user_row = usernames.index(user) + 2
                # acquire some data
                new_user = {
                	"username" : user,
                	"amazon_wishlist" : doc.cell(user_row, 11).value,
                	"verification_image" : doc.cell(user_row, 12).value
                }
                # save that data
                verified["verified_users"].append(new_user)
                verified["usernames"].append(user)
                saveJSON(verified, SubotSettings.VERIFIED_JSON)

                sub.set_flair(user, '', flairName)
                sendMessage(user, "Verified!", "Your verification request has been approved. Check /r/%s now to view your flair." % subreddit)
                logging.info("Verifying: %s at %s" %(user, strftime("%Y-%m-%d %H:%M:%S", gmtime())))

                checked_users.append(user)
                saveJSON(checked_users, SubotSettings.CHECKED_JSON)
        elif not approval:
        	if user not in checked_users:
	        	sendMessage(user, "%s Verification" % subreddit, "Your verification request has been rejected. Please [message the moderators](http://www.reddit.com/message/compose?to=%%2Fr%%2F%s) if you have any questions." % subreddit)
        		checked_users.append(user)
                saveJSON(checked_users, SubotSettings.CHECKED_JSON)

def getNewSubmissions(sub):
	global r
	subreddit = r.get_subreddit(sub)
	misc_save = loadJSON(SubotSettings.MISC_SAVE_JSON)
	submissions = []
	for submission in subreddit.get_new(limit=20, place_holder=misc_save["last_checked"]): # need to add a safety net here, in case the place_holder is not found
		if submission.id not in misc_save["processed_submissions"]: # only get ones you haven't commented on before
			submissions.append(submission)
	submissions.pop() # remove the last entry, because it includes the place_holder, which we don't want to check/comment on again
	return submissions

def processPosts(submissions):
	global r
	verified = loadJSON(SubotSettings.VERIFIED_JSON)
	verified_users = verified["verified_users"]
	misc_save = loadJSON(SubotSettings.MISC_SAVE_JSON)

	for submission in submissions:
		author_name = submission.author.name
		if author_name in verified["usernames"]:
			author_data = (user for user in verified_users if user["username"] == author_name).next()
			makeComment(submission, "The author of this thread is **verified**.\n\nAmazon Wishlist: %s\n\nVerification: %s" % (author_data["amazon_wishlist"], author_data["verification_image"]))
			misc_save["processed_submissions"].append(submission.id)
		# elif author_name not in verified["usernames"]:
			# makeComment(submission, "The author of this thread is **not** verified. Please submit a verification request.")
			# submission.remove() # send to mod queue

	misc_save["last_checked"] = submissions[0].id
	saveJSON(misc_save, SubotSettings.MISC_SAVE_JSON)

def checkModQueue(sub):
	for submission in sub.get_mod_queue():
		if submission.author.name in verified_users: # automatically approve submissions stuck in mod queue made by verified users
			makeComment(submission, "The author of this thread is **verified**.\n\nAmazon Wishlist: %s\n\nVerification: %s" % (author_data["amazon_wishlist"], author_data["verification_image"]))
			submission.approve()

def main():
    global r
    logging.info("Starting bot: " + strftime("%Y-%m-%d %H:%M:%S", gmtime()))

    # load things from settings
    sub = SubotSettings.SUBREDDIT

    while True:
        try:
            r = praw.Reddit(user_agent=SubotSettings.USER_AGENT)
            r.login(SubotSettings.REDDIT_USERNAME, SubotSettings.REDDIT_PASSWORD)
            break
        except Exception as e:
            logging.error('ERROR: {0}'.format(e))

    verifyUsers(sub)
    new_submissions = getNewSubmissions(sub)
    processPosts(new_submissions)

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
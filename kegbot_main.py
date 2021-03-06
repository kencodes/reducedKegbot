#!/usr/bin/env python2

# Used in scheduling
import time
from datetime import datetime, timedelta

# System modules
import os
from sys import platform as _platform

# For sending email
from smtplib import SMTP
from email.mime.text import MIMEText
import string

# For Twitter interface
from threading import Thread
from collections import deque
from requests.exceptions import ChunkedEncodingError
from twython import Twython, TwythonStreamer

# For parsing YAML files
import yaml

# Receiving sensor data from Arduino
import serial

# Scheduling tasks like sending status email
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
import logging
logging.basicConfig(filename='reducedKegbot.log',
                    filemode='a',
                    format='[%(asctime)s] %(message)s',
                    datefmt='%Y/%d/%m %H:%M:%S',
                    level=logging.WARNING)#.INFO)ERROR)CRITICAL)

# Regex for extracting data from Twitter control messages 
import re

# Pushbullet Interface
from pushbullet import Pushbullet

# Import JSON for communicating with website
import json

#####################################################
# Setup
#####################################################

# Project Path (on the Pi)
config_path = "/home/pi/prj/reducedKegbot"
os.chdir(config_path)

# Import secret configuration info from secret.yaml
secret_config_yaml = open(config_path+"/secret.yaml", 'r')
secret_config = yaml.load(secret_config_yaml)
secret_config_yaml.close()

# EMAIL
DISCOFRIDGE_ADMINS = secret_config['DISCOFRIDGE_ADMINS']
kb_email_addr = secret_config['kegbot_email_addr']
smtp_server = secret_config['smtp_server']

# Twitter info
APP_KEY = secret_config['APP_KEY']
APP_SECRET = secret_config['APP_SECRET']
OAUTH_TOKEN = secret_config['OAUTH_TOKEN']
OAUTH_TOKEN_SECRET = secret_config['OAUTH_TOKEN_SECRET']
TWITTER_SEARCH_TERM = secret_config['TWITTER_SEARCH_TERM']
# Twitter command format:
# #NUVATION_DISCOFRIDGE <tap>:<currentKegGallons>:<kegSizeGallons>:<ACTIVE | INACTIVE>:<date tapped>:<FullBeerName>:<Short Beer Name>
TWITTER_REGEX = r"#NUVATION_KEGBOT (\d):(\d+\.\d*):(\d+\.\d*):([a-zA-Z]+):(\d+/\d+/\d+):(.*):(.*)"
APPROVED_TWITTER_ADMINS = secret_config['APPROVED_TWITTER_ADMINS']
# Make a twitter object for SENDING tweets
twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)
# Pushbullet
PUSHBULLET_ACCESS_TOKEN = secret_config['PUSHBULLET_ACCESS_TOKEN']

# Import keg/tap info from taps.yaml
# taps_yaml = open(config_path+"/taps.yaml", 'r')
# taps = yaml.load(taps_yaml)
# taps_yaml.close()

taps_json = open(config_path+"/taps.json", 'r')
taps = yaml.load(taps_json)
taps_json.close()

# Import configuration from kegbot_config.yaml
kegbot_config_yaml = open(config_path+"/kegbot_config.yaml", 'r')
kb_config = yaml.load(kegbot_config_yaml)
kegbot_config_yaml.close()

# Flow meter pulse counts to volume conversion
cts_per_oz = kb_config['CTS_PER_OZ'] # ~170.5 pulses/oz.

# set greater than 0 to make things print out development messages
verbosity = kb_config['VERBOSITY']

# Send low keg warning when volume reaches this level
low_vol_thresh = kb_config['LOW_VOL_THRESH']

# How long to wait after no flow activity before updating taps.yaml
yaml_wait_time = kb_config['YAML_WAIT_TIME']

# Regex for parsing flow data from Arduino
FLOW_REGEX = r"tap1:(\d+) tap2:(\d+) tap3:(\d+) temp1:(\d+\.\d+) temp2:(\d+\.\d+) temp3:(\d+\.\d+)"

# Serial communication with sensor interface (Arduino)
serial_baud = kb_config['SERIAL_BAUD']
if _platform == "linux" or _platform == "linux2": # linux
    serial_port = kb_config['SERIAL_PORT_LINUX']
elif _platform == "win32": # Windows...
    serial_port = kb_config['SERIAL_PORT_WINDOWS']

# Declare Variables
tap_flow_counts = [0, 0, 0]
temperature = [0.0, 0.0, 0.0]


#####################################################
# Support Functions
#####################################################

def send_status_email():
    email_subject = ""
    email_body = ""
    # Generate subject line
    email_subject = generate_email_subject(taps)
    # Generate status email message body
    email_body = generate_email_body(taps)
    # send email update with volumes    
    send_email(kb_email_addr, DISCOFRIDGE_ADMINS, email_subject, email_body, smtp_server)

def generate_email_subject(taps_dict):
    subject = "Tap1:{0} Tap2:{1} Tap3:{2}".format(taps_dict[1][0], taps_dict[2][0], taps_dict[3][0])
    # Check if any taps should generate alert
    for tap in taps_dict:
        if taps_dict[tap][2] == "ACTIVE" and taps_dict[tap][0] < low_vol_thresh:
            subject = "LOW KEG ALERT"
            break
    return subject
    
def generate_email_body(taps_dict):
    '''
    Should use an enumerate() loop to iterate over the number of taps, for when there aren't 3 taps.
    
    '''
    body = '''
Tap 1, %s, %.2fgal (%.1fL) remaining\n
Tap 2, %s, %.2fgal (%.1fL) remaining\n
Tap 3, %s, %.2fgal (%.1fL) remaining''' % (taps_dict[1][4], taps_dict[1][0],
                                        (3.7854*taps_dict[1][0]),
                                        taps_dict[2][4], taps_dict[2][0],
                                        (3.785*taps_dict[2][0]),
                                        taps_dict[3][4], taps_dict[3][0],
                                        (3.785*taps_dict[3][0]))
    return body

def send_email(from_email, to_email, msg_subj, msg_body, mail_server):
    '''
    Sends an email to recipients(to_email), from the email address specified in
    argument from_email, with the given subject and body. Use the mail server
    specified in argument mail_server
    
    All arguments are given as strings
    '''
    BODY = string.join((
        "From: %s" % from_email,
        "To: %s" % to_email,
        "Subject: %s" % msg_subj ,
        "Body: %s" % msg_body
        ), "\r\n")
    s = SMTP(mail_server)
    s.sendmail(from_email, to_email, BODY)
    s.quit()

def convert_to_volume(flow_counts_list):
    '''
    Convert the number of pulses, sent by the arduino for each tap, to volume
    of beer poured. Use floats and ounces.
    '''
    # Determine volume poured on each tap
    for ii in range(len(flow_counts_list)):
        # Convert the counts to gallons poured for this tap
        ounces_poured = flow_counts_list[ii] / cts_per_oz
        gallons_poured = ounces_poured / 128
        # Update current gallons remaining for this keg
        taps[ii+1][0] = taps[ii+1][0] - gallons_poured
    
# def update_taps_yaml(taps_dict):
    # ''' 
    # Updates the taps.yaml file, which stores beer data
    # '''
    # if len(taps_dict) == 3:
        # with open('taps.yaml', 'w') as outfile:
            # outfile.write(yaml.dump(taps_dict, default_flow_style=False))
            # outfile.close()
    # elif len(taps_dict) == 0:
        # print("taps dictionary is empty! Won't write YAML")
    # else:
        # print("taps dictionary isn't empty, but doesn't have 3 elements")

def update_taps_json():
    ''' 
    Updates the taps.json file, which stores beer data
    '''
    with open('taps.json', 'w') as jsonfile:
        json.dump(taps, jsonfile, indent=4)
        jsonfile.close()

# def update_web_taps_json(taps_dict, temps):
def update_web_taps_json(temps):
    '''
    Updates the json file, which is used by the website to display beer data
    '''
    # temporary_dict = taps_dict.copy()
    temporary_dict = taps.copy()
    temporary_dict['temperature'] = temps
    with open('/var/www/html/taps.json', 'w') as jsonfile:
        json.dump(temporary_dict, jsonfile, indent=4)
        jsonfile.close()

def update_taps_dict(tap, current_keg_vol, total_keg_vol, is_active, date_tapped, long_name, short_name):
    '''
    Given a set of parameters for a single new keg, this function updates
    the taps.yaml to reflect that new keg
    '''
    # Edit the taps dictionary
    taps[tap][0] = current_keg_vol
    taps[tap][1] = total_keg_vol
    taps[tap][2] = is_active
    taps[tap][3] = date_tapped
    taps[tap][4] = long_name
    taps[tap][5] = short_name

def pushbullet_new_keg_update(taps, pb_object):
    '''
    Sends a pushbullet push over the kegerator channel
    '''
    pb_title = "New Keg!"
    pb_msg = "Tap 1: %s (%.2f gal.)\nTap 2: %s (%.2f gal.)\nTap 3: %s (%.2f gal.)" % (taps[1][5], taps[1][0], taps[2][5], taps[2][0], taps[3][5], taps[3][0])
    push = pb_kegbot_channel.push_note(pb_title, pb_msg)

def tweet_new_keg_update(taps, new_keg_tap_num):
    '''
    Sends a Tweet that a new keg has been added
    '''
    message = "#NuvationHasANewKeg\nTap 1: %s (%.2f gal.)\nTap 2: %s (%.2f gal.)\nTap 3: %s (%.2f gal.)" % (taps[1][5], taps[1][0], taps[2][5], taps[2][0], taps[3][5], taps[3][0])
    try:
        twitter.update_status(status=message)
    except TwythonError as e:
        print e

class TwitterStream(TwythonStreamer):
    '''
    Twython Twitter search object. This object searches the Twitter firehose for
    a specific search term and, if found, puts the associated Tweet in a queue
    '''
    def __init__(self, consumer_key, consumer_secret, token, token_secret, tqueue):
        self.tweet_queue = tqueue
        super(TwitterStream, self).__init__(consumer_key, consumer_secret, token, token_secret)

    def on_success(self, data):
        if 'text' in data:
            self.tweet_queue.append(data)

    def on_error(self, status_code, data):
        print(status_code)
        # Want to stop trying to get data because of the error?
        # Uncomment the next line!
        # self.disconnect()

def stream_tweets(tweets_queue):
    '''
    A queue that holds Tweets which contain the Twitter search term "#NUVATION_KEGBOT"
    '''
    try:
        stream = TwitterStream(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET, tweets_queue)
        stream.statuses.filter(track=TWITTER_SEARCH_TERM)
    except ChunkedEncodingError:
        # Sometimes the API sends back one byte less than expected which results in an exception in the
        # current version of the requests library
        stream_tweets(tweet_queue)

def tweet_checker(tweets_queue):
    '''
    When an element is found in the queue, this function parses that tweet
    according to a Regex string and saves the extracted data. It then updates
    the taps dictionary, taps.yaml, taps.json and sends confirmation Tweets
    and Pushbullets
    '''
    if len(tweets_queue) > 0:
        new_tweet = tweets_queue.popleft()
        if 'text' in new_tweet:
            check_tweet = new_tweet['text'].encode('utf-8')
            # Check whether the expression matches the date string
            if re.search(TWITTER_REGEX, check_tweet):
                if new_tweet['user']['screen_name'].lower() in APPROVED_TWITTER_ADMINS:
                    # Extract data from tweet
                    m = re.search(TWITTER_REGEX, check_tweet)
                    tap = int(m.group(1)) # Int tap number
                    current_keg_vol = float(m.group(2)) # Float current volume
                    total_keg_vol = float(m.group(3)) # Float starting volume
                    is_active = m.group(4) # string
                    date_tapped = m.group(5) # string
                    long_name = m.group(6) # string
                    short_name = m.group(7) # string
                    # Update beer dictionary
                    update_taps_dict(tap, current_keg_vol, total_keg_vol, is_active, date_tapped, long_name, short_name)
                    # Update beer database (YAML)
                    # update_taps_yaml(taps)
                    update_taps_json()
                    # Update beer database (JSON) for website
                    update_web_taps_json(temperature)
                    # Print update status to console and send update success tweet to user
                    message = "successfully put %.2f gal. (%.1fL) of %s on Tap #%d" % (current_keg_vol, current_keg_vol*3.785, long_name, tap)
                    tweet_confirm_success(new_tweet, message)
                    # Send public update tweet and pushbullet
                    tweet_new_keg_update(taps, tap)
                    pushbullet_new_keg_update(taps, pb)
                # Correct Regex, but from UNAPPROVED admin. They must be abused.
                else:
                    message = "You are not an approved Discofridge admin"
                    tweet_confirm_success(new_tweet, message)
            else:
                print("Twitter Regex mismatch! Tweet contains {}".format(check_tweet))
        else:
            print("Tweet does not contain text")

def tweet_confirm_success(tweet, msg):
    '''
    Sends a confirmation tweet in response to received command tweet.
    Include date/time to ensure each tweet is unique and does not get rejected
    '''
    formattedTime = datetime.now().strftime('%x %X')
    message = "@{0} {1} on {2}".format(tweet['user']['screen_name'], msg, formattedTime)
    print(message)
    try:
        twitter.update_status(status=message)
    except:
        print("Some kind of twitter error. Is beer name too long?")
        
#####################################################
# Program Setup
#####################################################

# Configure serial interface to Arduino (for sensors)
try:
    ser = serial.Serial(serial_port, serial_baud)
    if ser.isOpen():
        time.sleep(1)
        ser.flushInput()
        print(ser.name + ' is flushed and open at {}bd'.format(serial_baud))
except:
    print("Error opening serial connection")

# Make a Pushbullet object
try:
    pb = Pushbullet(PUSHBULLET_ACCESS_TOKEN)
    pb_kegbot_channel = pb.channels[0]
except:
    print("Could not start pushbullet interface")


#####################################################
# Main Program Loop
#####################################################
flow_temp_data = ""
flow_temp_text = ""

if __name__ == '__main__':
    # print("Length of taps.yaml: {}".format(len(taps)))
    # Start Email scheduler
    sched = BackgroundScheduler()
    sched.add_job(send_status_email, 'cron', hour='8') #GMT??? How to set timezone?
    sched.start()
    # Create Tweets Queue
    tweet_queue = deque()
    # Create twitter search thread and start the stream search
    tweet_stream = Thread(target=stream_tweets, args=(tweet_queue,))
    tweet_stream.daemon = True
    tweet_stream.start()
    # Update taps.json to ensure website is accurate
    # print("Length of taps.yaml: {}".format(len(taps)))
    update_web_taps_json(temperature)
    # print("Length of taps.yaml: {}".format(len(taps)))
    try:
        print("Waiting for flow or Tweets...")
        while True:
            # if len(taps) != 3:
                # print("Length of taps.yaml: {}".format(len(taps)))
                # print(taps)
                # break
        ########### Check Flow Meters ##############
            # Read flow data from serial interface
            # If data waiting in serial buffer
            bytesToRead = ser.inWaiting()
            if (bytesToRead>0):  
                try:
                    flow_temp_data = ser.readline().strip()
                    # Use regex search to extract flow count for each tap
                    if re.search(FLOW_REGEX, flow_temp_data):
                        flow_temp_text = re.search(FLOW_REGEX, flow_temp_data)
                        # Save flow data to a list
                        tap_flow_counts = [int(flow_temp_text.group(1)), int(flow_temp_text.group(2)), int(flow_temp_text.group(3))]
                        temperature = [float(flow_temp_text.group(4)), float(flow_temp_text.group(5)), float(flow_temp_text.group(6))]
                        # Convert tap_flow_counts[] to volume and update yaml/json files
                        if (tap_flow_counts[0]>10 or tap_flow_counts[1]>10 or tap_flow_counts[2]>10):
                            convert_to_volume(tap_flow_counts)
                            # update_taps_yaml(taps)
                            update_taps_json()
                        update_web_taps_json(temperature)
                    else:
                        print("Regex problem, found string: {}".format(flow_temp_text))
                except KeyboardInterrupt:
                    print("Press Ctrl+C again to quit")
                    time.sleep(2)
                except: # Default except
                    print("Problem reading serial data! Found: {0}".format(flow_temp_data))
                    time.sleep(1)
                
        ########### Check tweet queue ##############
            if len(tweet_queue) > 0:
                # Send tweet to tweet_checker
                tweet_checker(tweet_queue)

    except (KeyboardInterrupt, SystemExit):
        # Update and close taps.yaml
        # print("Updating taps.yaml")
        # if len(taps)==3:
            # update_taps_yaml(taps)
            # update_web_taps_json(temperature)
        # else:
            # print("taps dictionary length is currently {0}!!!".format(len(taps)))
        
        # Stop Cron Scheduler
        print("Shutting down cron scheduler...")
        sched.shutdown()
        
        # Close Serial
        print("Closing serial connection...")
        ser.close()
        
        # print("Final length of taps.yaml: {}".format(len(taps)))
        

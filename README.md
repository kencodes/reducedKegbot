# README #
Discofridge (reducedKegbot) is a fork of an earlier Nuvation project, Kegbot. It runs on a Raspberry Pi and reads flow meters that are connected to our beer taps. Its purpose is to report what is on tap and how much is left.

### To Do ###
* Write script to update python and html files from git
 * User must run script manually to update the files
* Add gas shutoff valves to leftside kegerator, one after regulator, one on each side of Wye
* Make browser run at boot and show http://localhost in fullscreen mode
* Determine why taps.yaml gets erased
* Fix timestamp in "successfully added keg" tweet to local time zone
* Fix cron scheduler for email to reference local time zone
* How many bytes should be in an arduino message?
 * Should only pop one message at a time?
 * Put bytes in a queue and have a separate function pull bytes out of the queue one full message (flow+temperature) at a time?
* Save taps.yaml to tapsBackup/taps_<date>.yaml, once/day, when email status is sent, to have a record of daily consumption
 * Used to restore taps.yaml if it is erased
 * send console/email/twitter message if script had to restore from taps.yaml.backup
 * Save taps.yaml.backup as the daily yaml backup (tapsBackup/taps<date>.yaml is the record keeping)
 * On script startup, and periodically, check if len(taps)==0 and, if so, restore from taps.yaml.backup
* Rebuild breadboard as soldered perfboard with connectors to flowmeters/temperature sensor
 * Extend temp sensor cable

### Done ###
* Add Arduino code to this repo
* Add temperature sensor interface to Arduino
* Make kiosk display remove cursor from middle of screen
* At kegbot_main.py exit, update taps.yaml (if len()==3)
* Remove print(taps) when program runs
* Add support for temp sensors 2 and 3 in Arduino code
* Update Arduino Regex search to support 3 temperature sensors

### What is this repository for? ###
* All python and related source files
* Arduino source code
* The web interface code is in a separate repo, called reducedKegbotWeb

### How do I get set up? ###
* (TBD) Configuration
 * Discofridge (Nuvation Kegbot) is implemented using:
   * Raspberry Pi Model 1B running Raspbian Jessie for the main computing and web interface
   * Arduino Uno R3 for hardware interface, flow meter pulse counter, temperature sensor i/f, 5V->3.3V conversion, serial-USB i/f
   * Swiss Flow SF800 flow meters
   * DS18B20 temp sensors
   * Wall mounted ViewSonic VG2021m with integrated speakers as the display
 * crontab is used to automatically launch the kegerator scripts at Raspberry Pi bootup. Use `<sudo crontab -e>` to show the crontab file on the Pi, then verify the following lines are added to the bottom of the file.
```
@reboot sudo python /home/pi/prj/reducedKegbot/kegbot_main.py >/home/pi/logs/cronlog 2>&1
```
 * Launch Midori in fullscreen mode at startup
  * <instructions>
 * Run Unclutter at startup to remove the cursor from the middle of the screen
  * <instructions>
  * Add '''@unclutter -idle 0.1 -root''' to /etc/xdg/lxsession/LXDE/autostart
 
 
 
* Dependencies
 * The following python2 modules will need to be installed
  * Twython `pip install twython`
  * Pushbullet `pip install pushbullet.py`
  * YAML `http://pyyaml.org/wiki/PyYAML`
  * APScheduler `pip install apscheduler`
  * Regex `pip install regex`
 * Non-python dependencies...
  * Javascript, css/bootstrap, etc?
* Database configuration
 * (TBD)
* How to run tests
 * (TBD)
* Deployment instructions
 * (TBD)
 
 
### secret.yaml ###
The contents of this file are secret and are, therefore, not included in the git repository.  Instead, a symlink is checked into git, which references the actual secret.yaml file, which is in the next directory up from reducedKegbot.  The structure of the real secret.yaml is as follows:

```yaml
# Administrator Email, Must be saved as lower case
DISCOFRIDGE_ADMINS:
    - name1@domain.com
    - name2@domain.com

# Twitter usernames, excluding the '@' symbol
APPROVED_TWITTER_ADMINS:
    - handle1
    - handle2

# Kegbot's email address, this just appears in the "from" field
# in email sent from the kegerator
kegbot_email_addr: Kegbot@domain.com

# EMAIL SERVER
smtp_server: server.domain.com

# Twython will search Twitter for this term. I used a hashtag with the kegerator name
TWITTER_SEARCH_TERM: '#HASHTAG'

# Twitter application authentication, get these from twitter when you sign up
# as a developer. Garbage text is shown here
APP_KEY : 2lkjagFSADGjg094alkjgn2
APP_SECRET: j2$TJas;lgij234lkjfdalkjlaf24:LAKjL:KHg323r
OAUTH_TOKEN: 9843659032-jASGFJ3roiguvfjbjj394agj;
OAUTH_TOKEN_SECRET: 908slkfdn34AL":JspuqgnqEGQKwrg'qi3ocn;

# Pushbullet Access Token. Get this from Pushbullet when you sign up as an admin
PUSHBULLET_ACCESS_TOKEN: 's.234jkDLKFJ93fvkwlhasdiu'
```

### Contribution guidelines ###
Suggestions and contributions are welcome and encouraged.  The purpose of this doing this project was for me to try to learn basic software design using a project-based approach. I would appreciate hearing about anything you see wrong with the project or anything that could be improved.

### Who do I talk to? ###
* Repo owner or admin (me)
* Visit blog.Nuvation.com to read about our earlier Kegbot project, which included electronic payments, SQL databases of users, beers, and taps, access control using solenoidal valves and which had a pretty web interface.

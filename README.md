# README #
Discofridge (reducedKegbot) is a fork of an earlier Nuvation project, Kegbot. It runs on a Raspberry Pi and reads flow meters that are connected to our beer taps. Its purpose is to report what is on tap and how much is left.

### To Do ###
* Finish renaming from reducedKegbot or kegbot to DiscoFridge
* Add Arduino code to this repo
* Add temperature sensor interface to Arduino
* Write script to update python and html files from git
  * User must run script manually to update the files
* Add shutoff valves to leftside kegerator, one after regulator, one on each side of Wye

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

### Contribution guidelines ###
Suggestions and contributions are welcome and encouraged.  The purpose of this doing this project was for me to try to learn basic software design using a project-based approach. I would appreciate hearing about anything you see wrong with the project or anything that could be improved.

### Who do I talk to? ###
* Repo owner or admin (me)
* Visit blog.Nuvation.com to read about our earlier Kegbot project, which included electronic payments, SQL databases of users, beers, and taps, access control using solenoidal valves and which had a pretty web interface.

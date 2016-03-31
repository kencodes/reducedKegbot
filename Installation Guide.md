# Installation Guide #
This document is intended to list all the steps required to install Discofridge
("reducedKegbot") on a new Ubuntu 16.04LTS system.


### apps to install ###
* Google Chrome
 * from the software store
* Nginx
 * sudo apt-get install -y nginx
* git
 * sudo apt-get install -y git
* pip
 * sudo apt-get install -y python-pip

* Create cron job
 * crontab -e
  * @reboot /home/prj/runDiscofridge.sh
* Modify the launcher shell script
 * Change ~/prj/runDiscofridge.sh to point 

### Get python source ###
* git clone https://github.com/kencodes/reducedKegbot.git /home/discofridge/prj
* Modify /home/discofridge/prj/kegbot_main.py
 * change config_path = "<your path to this file>"


### Get and modify web source ###
* git clone https://github.com/kencodes/reducedKegbotWeb.git /var/www/html
* 

### System Changes ###
* Install setuptools for python
 * sudo apt-get install python-setuptools
* Install YAML for python
 * sudo pip install PyYAML
* Install Twython (Twitter interface)
 * pip install twython
* Install Python Requests
 * pip install requests
* Install Python Pushbullet Interface
 * pip install pushbullet.py
*? Install python-magic as a requirement for running pushbullet.py
 * apt-get install python-magic
* Install regular expression library for python
 * pip install regex
* Install serial module for Python
 * pip install pyserial
* Install APScheduler
 * pip install apscheduler



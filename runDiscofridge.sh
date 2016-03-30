#!/bin/bash

# Add to crontab -e
# @reboot /home/prj/runDiscofridge.sh

# zotac wireless MAC:  74:2f:68:af:cf:22
#       hard wire MAC: 00:01:2e:3a:e6:65

# Run the python script
sudo python /home/discofridge/prj/kegbot_main.py &

# Open the browser in kiosk mode
google-chrome --kiosk http://localhost
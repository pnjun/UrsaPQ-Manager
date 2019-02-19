Manager Service
=======

This serivce is run by systemd on the Unix server mounted in the experimental rack. It provides an unified interface to the experimental setup to all connected consoles and user scripts, as well as managing the sample oven temperature control loop and the high voltage power supplies.

It runs automatically at startup and is automatically restarted in case if fails.

## Start / Stop / Restart

The service can be started stopped and restarted with:
* `sudo systemctl start ursapqManager.service`
* `sudo systemctl stop ursapqManager.service`
* `sudo systemctl restart ursapqManager.service`

## Source location
The soruce code for the server process is located in ~/ExpManager/Modules/. The server script is ursapqManager.py

# twobit-stm
**Simple Screen Time Manager**

This project is a simple set of three tools to manage screen time for kids.
 * A server that tracks time spent by users that have a corresponding server side configuration
 * A client that pings the server every 30 seconds (configurable) while the user is actively using the computer. Once the allotted time runs out, the client shuts down the computer.
 * A small GUI tool that shows the user how much time is left of the allotted time.
  
  The client is a Windows service that runs irrespective of which user is logged in. The server side of things may be run on a Windows machine too (including the machine running the client). The GUI tool (monitor) is only intended to help the end user keep track of how much time is left. Nothing is persisted, so if the server is restarted, the registered users get a fresh lease.
  
  Neither the client nor the server are written to be bulletproof by any means. They are intended to help my kids - and maybe yours - spend less time in front of their computers.
  
  Everything is written in Python and super simple to customize to your needs. I will be adding an installation guide here - it is not terribly complicated, but getting a Python Windows service running requires a little work.
  
  ==Simple installation guide==
  
  Installing the server is pretty simple (on Ubuntu):
  * Put the project files in /opt/stm or something similar
  * copy the stm.service script to /etc/system.d/system and check paths and such are correct
  * run systemctl daemon-reload
  * copy the stm-server.config to /etc
  * install Python 3.6 or higher if it isn't already
  * use pip to install websockets
  * try to run the service using plain Python like: python3 stm-server.py - check the output for errors (also the log file)
  * try running the service using systemctl start stm.service
  
  If all that works, all you have to do is figure out what the local username of the accounts you wish to limit are. Do this by running 'set' from the command prompt in Windows. The USERNAME variable has the bit you want. Modify stm-server.config to match the names and times you want.
  
  

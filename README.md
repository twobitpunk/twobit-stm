# twobit-stm
# Simple Screen Time Manager

This project is a simple set of three tools to manage screen time for kids.
 * A server that tracks time spent by users that have a corresponding (very simple) server side configuration.
 * A client that pings the server at intervals while the user is actively using the computer. Once the allotted time runs out, the client shuts down the computer.
 * A small GUI tool that shows the user how much time is left of the allotted time.
  
I tried several commercial screen time management tools like Microsoft Family and Kaspersky Safe Kids but they really didn't work too well and they are also a bit creepy to be honest.

  The twobit-stm client is a Windows service that runs irrespective of which user is logged in. The server side of things may be run on pretty much anything (including the machine running the client). The GUI tool (monitor) is only intended to help the end user keep track of how much time is left. Nothing is persisted, so if the server is restarted, the registered users get a fresh lease.
  
  Everything is written in Python and super simple to customize to your needs. Have a look at the installation guide below - it is not terribly complicated, but getting a Python Windows service running requires a little work.
  
## Simple installation guide
  
### Server
  Installing the server is pretty simple (on Ubuntu):
  * Put the project files in `/opt/stm` or something similar
  * copy or link the `stm.service` script to `/etc/systemd/system` and check that paths and such are correct
  * run `systemctl daemon-reload`
  * copy the `stm-server.config` to `/etc` - edit to suit your fancy
  * install Python 3.6 or higher if it isn't already
  * use Python `pip` to install `websockets`
  * try to run the service using plain Python like: `python3 stm-server.py` - check the output for errors (also the log file)
  * try running the service using `systemctl start stm.service`
  * If that works, you can enable autostart of the service by running `systemctl enable stm.service`
  
  If all that works, all you have to do is figure out what the local usernames of the accounts you wish to limit are. Do this by running `set` from the command prompt in Windows. The `USERNAME` variable has the bit you want. Modify `stm-server.config` to match the names and times you want. You can also use MS account names if you like. This is the better choice if your kids use more than one computer.
  
### Client
  Installing the client is also fairly simple:
  * Install Python >=3.6
  * Use `pip` (from in the scripts subfolder of you Python installation) to install `pywin32` and `websockets`
  * Still in the scripts folder, run `python pywin32_postinstall.py -install` to put PyWin32 files in the right places.
  * Put the `twobit-stm` project files in a folder - or just use the checkout folder
  * Open a command prompt with administrator rights and go to the `twobit-stm\client` folder
  * Run `python stm-client.py install` and watch the output. There should be no errors
  * Make the `c:\etc` directory if you haven't got one and put the `stm-client.config` in it.
  * Check that the client configuration is pointing at the server installation.
  * Press `Win+R` and run `services.msc` - find the Screen Time Manager Service and start it.
  
  Check the output of client and server to see if they are communicating properly. If the client service refuses to start, you can run it from the command line with the debug option like so: `python stm-client.py debug`. This lets you see what is going on.
  
### Monitor GUI
  The monitor GUI app shares configuration with the client service. It may be run directly as `python stm_client_monitor.py` from the command line or a shortcut. It is really simple and it doesn't log anything. 
  
### Notes
  My client machines are running Windows 10 and the server is a RasPi that is doing lots of other things too. The server can also be run on Windows if you want.
  
  Neither the client nor the server are written to be bulletproof by any means. They are intended to help my kids - and maybe yours - spend less time in front of their computers. There are quite a few ways of fooling the client into thinking sessions are locked, the server isn't running and so on. Some I may fix - but so far, this is intended for home use in a not too hostile setting.
  
  That should be it! I have probably forgotten something - I will improve this along the way. Comments and suggestions are very welcome :-)
  
  
  

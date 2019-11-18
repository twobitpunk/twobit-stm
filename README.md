# twobit-stm
**Simple Screen Time Manager**

This project is a simple set of three tools to manage screen time for kids.
 * A server that tracks time spent by users that have a corresponding server side configuration
 * A client that pings the server every 30 seconds (configurable) while the user is actively using the computer. Once the allotted time runs out, the client shuts down the computer.
 * A small GUI tool that shows the user how much time is left of the allotted time.
  
  The client is a Windows service that runs irrespective of which user is logged in. The server side of things may be run on a Windows machine too (including the machine running the client). The GUI tool (monitor) is only intended to help the end user keep track of how much time is left. Nothing is persisted, so if the server is restarted, the registered users get a fresh lease.
  
  Neither the client nor the server are written to be bulletproof by any means. They are intended to help my kids - and maybe yours - spend less time in front of their computers.
  
  Everything is written in Python and super simple to customize to your needs. I will be adding an installation guide here - it is not terribly complicated, but getting a Python Windows service running requires a little work.
  

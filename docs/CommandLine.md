---
page_icon: img/commandline.jpg
---
{% include pageIcon.html %}
## Command-Line Configuration of PiPedal

The pipedalconfig program can be used to modify configuration of PiPedal from a shell command line. Run 'pipedalconfig --help' to view
available configuration commands, some of which are not available from the web interface. For example, you can change the port number
of the Web App HTTP server if you need to, using pipedalconfig.
     
Things you can do with pipedalconfig:
     
     - Stop, start or restart the PiPedal services.
     
     - Choose whether to automatically start PiPedal services on reboot.
     
     - Select an alternate web server port.
     
     - enable or disable the Wi-Fi hotspot.

     - enable or disable Bluetooth remote access (`--enable-bluetooth` / `--disable-bluetooth`) so an iPad can stay on Wi-Fi for internet.
     
Run `pipedalconfig --help` for available options.

--------
[<< Optimizing Audio Latency](AudioLatency.md)  | [Up](Documentation.md) | [Changing the Web Server Port >>](ChangingTheWebServerPort.md)
     

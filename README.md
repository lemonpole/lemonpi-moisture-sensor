This script assumes a moisture detector is connected to GPIO17 on a Raspberry Pi. Sensor is below:
http://a.co/21NN4yP

The moisture sensor is activated when removed from water or the moisture level reaches
below the threshold. When this happens an e-mail is sent.

**DEPENDENCIES:**
- Python `2.7.9`
- Raspbian GNU/Linux 8 (jessie)
```bash
$ sudo pip install python-dotenv
$ sudo pip install jinja2
$ sudo pip install adafruit-mcp3008
```

**Globally available as a script**
```bash
$ sudo -i
$ PROJECT_ROOT=/home/pi/Projects/moisture-sensor
$ ln -s $PROJECT_ROOT/app.py /usr/local/bin/moisture-sensor
$ chmod +x /usr/local/bin/moisture-sensor
$ exit
```

--------------------

**NOTE:** GPIO 2/3 are reserved for devices with hard-wired pull-ups.

**NOTE:** To use Amazon SES a TXT Record must be added to Namecheap's DNS Entries. Also, free-tier limits the FROM/TO to **verified** e-mails only. To send from `plantbot@my-domain.com`:

1. Create a catch-all redirect e-mail on namecheap and point it to gmail
2. Send verification e-mail to the above from the Amazon SES console
3. ???
4. Profit.

--------------------

To read specific moisture levels the sensor's analog signal must be used. Unfortunately, Raspberry PI doesn't support analog ootb so the following are needed:
- Adafruit MCP3008 (ADC): https://www.adafruit.com/product/856
- Half/Full breadboard: http://a.co/7MVedwJ

Adafruit provides an easy to use library to interact with the MCP3008 and get readings from its channels. Along with examples:
https://github.com/adafruit/Adafruit_Python_MCP3008

**Wire up the MCP3008**

https://learn.adafruit.com/raspberry-pi-analog-to-digital-converters/mcp3008#wiring

*NOTE: I used hardware SPI which needs to be enabled:*

http://www.raspberrypi-spy.co.uk/2014/08/enabling-the-spi-interface-on-the-raspberry-pi/

--------------------

**Resources**

- https://www.modmypi.com/blog/raspberry-pi-plant-pot-moisture-sensor-via-analogue-signals
- https://www.raspberrypi.org/forums/viewtopic.php?t=55754
- https://www.raspberrypi-spy.co.uk/2013/10/analogue-sensors-on-the-raspberry-pi-using-an-mcp3008/
- https://computers.tutsplus.com/tutorials/build-a-raspberry-pi-moisture-sensor-to-monitor-your-plants--mac-52875

--------------------

- [ ] **TODO:** better error handling for when device not found on configured GPIO#
- [ ] **TODO:** calibrate it to soil: ~497-600 when soil is recently watered. slowly goes up to ~850 over 4hours
- [x] ~~**TODO:** can we pull specific moisture levels? (See links below)~~
- [ ] **TODO:** upgrade to python 3?
- [ ] **TODO:** keep count of warnings. if reached threshold send an e-mail
- [ ] **TODO:** limit e-mails via configuration variables
- [ ] **TODO:** non-blocking keyboard input using threads (https://stackoverflow.com/a/19655992)
- [x] ~~**TODO:** better logging for monitoring battery usage and soil calibration~~
- [ ] **TODO:** https://setuptools.readthedocs.io/en/latest/setuptools.html
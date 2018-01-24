#!/usr/bin/env python
"""
This script assumes a moisture detector is connected to SPI on the Raspberry Pi 3. Sensor is below:
http://a.co/21NN4yP

The moisture sensor is activated when removed from water or the moisture level reaches
below the threshold. When this happens an e-mail is sent.

_Table of measurements and average readings to come..._

## Dependencies
- Python `2.7.9`
- Raspbian GNU/Linux 8 (jessie)
  - with [hardware SPI enabled](https://www.raspberrypi-spy.co.uk/2014/08/enabling-the-spi-interface-on-the-raspberry-pi/)
```bash
$ sudo pip install jinja2
$ sudo pip install adafruit-mcp3008
```

### Globally available as a script
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

**NOTE:** When adding the TXT record on Namecheap ignore amazon's `_amazonses.yourdomain.*` TXT name value and just put `@` in the host column

1. Create a catch-all redirect e-mail on namecheap and point it to gmail
2. Send verification e-mail to the above from the Amazon SES console
3. ???
4. Profit.

## Hardware Requirements

To read specific moisture levels the sensor's analog signal must be used. Unfortunately, Raspberry PI doesn't support analog ootb so the following are needed:
- Adafruit MCP3008 (ADC): https://www.adafruit.com/product/856
- Half/Full breadboard: http://a.co/7MVedwJ
- Link to image of circuit coming soon...

Adafruit provides an easy to use library to interact with the MCP3008 and get readings from its channels. Along with examples:
https://github.com/adafruit/Adafruit_Python_MCP3008

### Wire up the MCP3008

https://learn.adafruit.com/raspberry-pi-analog-to-digital-converters/mcp3008#wiring

*NOTE: I used hardware SPI which needs to be enabled:*

http://www.raspberrypi-spy.co.uk/2014/08/enabling-the-spi-interface-on-the-raspberry-pi/

## Resources

- https://www.modmypi.com/blog/raspberry-pi-plant-pot-moisture-sensor-via-analogue-signals
- https://www.raspberrypi-spy.co.uk/2013/10/analogue-sensors-on-the-raspberry-pi-using-an-mcp3008/
- https://computers.tutsplus.com/tutorials/build-a-raspberry-pi-moisture-sensor-to-monitor-your-plants--mac-52875
"""
from __future__ import print_function

import os
import sys
import time
import smtplib
import logging
import logging.handlers
import argparse
import ConfigParser

from threading import Event
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from colorama import Fore, Style
from jinja2 import Environment, FileSystemLoader

import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008

class SDIMoistureSensor( object ):
    def __init__( self ):
        self.channel = 0
        self.spi_port = 0
        self.spi_device = 0
        self.polling_rate = 0.5
        self._on_moisture_gain = Event()
        self._on_moisture_loss = Event()
        self.mcp3008 = Adafruit_MCP3008.MCP3008( spi=SPI.SpiDev( self.spi_port, self.spi_device ) )

    @property
    def on_moisture_gain( self ):
        return self._on_moisture_gain

    @property
    def on_moisture_loss( self ):
        return self._on_moisture_loss

    @on_moisture_gain.setter
    def on_moisture_gain( self, value ):
        self._on_moisture_gain = value

    @on_moisture_loss.setter
    def on_moisture_loss( self, value ):
        self._on_moisture_loss = value

    def run( self ):
        prev_value = -1

        while True:
            value = self.mcp3008.read_adc( self.channel )

            if value != prev_value:
                if value < prev_value:
                    self._on_moisture_gain( value )
                elif value > prev_value:
                    self._on_moisture_loss( value )

            prev_value = value
            time.sleep( self.polling_rate )

class Config( object ):
    def __init__( self, args, ini_fullpath=None ):
        self.ini_fullpath = ini_fullpath
        self.args = args
        self.config_parser = ConfigParser.ConfigParser()
        self.config_parser.read( ini_fullpath )

    def get_config( self, name, default_val, cmd_line=True, env_var=False, ini=False, ini_section=None, ini_bool=False ):
        '''
        depending on predicates above(cmd_line, env_var, ini) will consider the precedence order:
            - looks for command line arg
            - looks for for environment variable
            - looks for ini in specified path
            - finally defaults to provided
            - if nothing found, throw exception
        '''
        # does it exist in the app args?
        if cmd_line and getattr( self.args, name.lower() ) is not None:
            return str( getattr( self.args, name.lower() ) )

        if env_var and name in os.environ:
            return str( os.getenv( name ) )

        if ini and self.config_parser.get( ini_section, name ) > -1:
            if ini_bool:
                return self.config_parser.getboolean( ini_section, name )
            else:
                return str( self.config_parser.get( ini_section, name ) )

        return str( default_val )


class DefaultValues( object ):
    PWD_PATH = os.path.dirname( os.path.realpath( __file__ ) )
    CHANNEL = 0
    SPI_PORT = 0
    SPI_DEVICE = 0
    POLLING_RATE = 5
    LOG_ENABLE = True
    LOG_MAXSIZE = 100
    LOG_PATH = '/var/log/moisture-sensor'
    SMTP_HOST = 'email-smtp.us-east-1.amazonaws.com'
    SMTP_PORT = 587
    SMTP_USER = 'user'
    SMTP_PASS = 'password'
    SMTP_FROM = 'Mr. Plant Bot <plantbot@your.domain>'
    SMTP_TO = 'you@domain.com'
    EMAIL_SUBJECT = 'Moisture Sensor Notification'
    EMAIL_TMPL_FILENAME = 'no-moisture.email.html'

# declare app args
ARGPARSER = argparse.ArgumentParser( description='Yooo. I do some stuff right here...' )
ARGPARSER.add_argument( '--channel', help='Change channel', type=int )
ARGPARSER.add_argument( '--spi-port', help='SPI Port', type=int )
ARGPARSER.add_argument( '--spi-device', help='SPI Device', type=int )
ARGPARSER.add_argument( '--polling-rate', help='Polling Rate', type=int )
ARGPARSERCONFIG = Config( ARGPARSER.parse_args(), ini_fullpath=os.path.join( DefaultValues.PWD_PATH, os.path.basename( __file__ ) + '.ini' ) )

# load configuration
CHANNEL = int( ARGPARSERCONFIG.get_config( 'CHANNEL', default_val=DefaultValues.CHANNEL, env_var=True, ini=True, ini_section='IO' ) )
SPI_PORT = int( ARGPARSERCONFIG.get_config( 'SPI_PORT', default_val=DefaultValues.SPI_PORT, env_var=True, ini=True, ini_section='IO' ) )
SPI_DEVICE = int( ARGPARSERCONFIG.get_config( 'SPI_DEVICE', default_val=DefaultValues.SPI_DEVICE, env_var=True, ini=True, ini_section='IO' ) )
POLLING_RATE = float( ARGPARSERCONFIG.get_config( 'POLLING_RATE', default_val=DefaultValues.POLLING_RATE, env_var=True, ini=True, ini_section='IO' ) )

EMAIL_SUBJECT = str( ARGPARSERCONFIG.get_config( 'EMAIL_SUBJECT', default_val=DefaultValues.EMAIL_SUBJECT, cmd_line=False, ini=True, ini_section='EMAIL' ) )
EMAIL_TMPL_FILENAME = str( ARGPARSERCONFIG.get_config( 'EMAIL_TMPL_FILENAME', default_val=DefaultValues.EMAIL_TMPL_FILENAME, cmd_line=False, ini=True, ini_section='EMAIL' ) )
SMTP_HOST = str( ARGPARSERCONFIG.get_config( 'SMTP_HOST', default_val=DefaultValues.SMTP_HOST, cmd_line=False, ini=True, ini_section='EMAIL' ) )
SMTP_PORT = int( ARGPARSERCONFIG.get_config( 'SMTP_PORT', default_val=DefaultValues.SMTP_PORT, cmd_line=False, ini=True, ini_section='EMAIL' ) )
SMTP_USER = str( ARGPARSERCONFIG.get_config( 'SMTP_USER', default_val=DefaultValues.SMTP_USER, cmd_line=False, ini=True, ini_section='EMAIL' ) )
SMTP_PASS = str( ARGPARSERCONFIG.get_config( 'SMTP_PASS', default_val=DefaultValues.SMTP_PASS, cmd_line=False, ini=True, ini_section='EMAIL' ) )
SMTP_FROM = str( ARGPARSERCONFIG.get_config( 'SMTP_FROM', default_val=DefaultValues.SMTP_FROM, cmd_line=False, ini=True, ini_section='EMAIL' ) )
SMTP_TO = str( ARGPARSERCONFIG.get_config( 'SMTP_TO', default_val=DefaultValues.SMTP_TO, cmd_line=False, ini=True, ini_section='EMAIL' ) )

LOG_ENABLE = bool( ARGPARSERCONFIG.get_config( 'LOG_ENABLE', default_val=DefaultValues.LOG_ENABLE, cmd_line=False, ini=True, ini_section='LOGGING', ini_bool=True ) )
LOG_MAXSIZE = int( ARGPARSERCONFIG.get_config( 'LOG_MAXSIZE', default_val=DefaultValues.LOG_MAXSIZE, cmd_line=False, ini=True, ini_section='LOGGING' ) )
LOG_PATH = str( ARGPARSERCONFIG.get_config( 'LOG_PATH', default_val=DefaultValues.LOG_PATH, cmd_line=False, ini=True, ini_section='LOGGING' ) )

# instantiate objects based off of provided configuration above
LOG_FILENAME = str( os.path.basename( __file__ ) + '.log' )
LOG_FULLPATH = LOG_PATH + '/' + LOG_FILENAME
LOG_FORMAT = logging.Formatter( '%(asctime)s %(message)s', "%Y-%m-%d %H:%M:%S" )
LOGGER = logging.getLogger( LOG_FILENAME )

MESSAGE_OBJ = MIMEMultipart( 'alternative' ) # contains text/plain and text/html
MESSAGE_OBJ[ 'Subject' ] = EMAIL_SUBJECT
MESSAGE_OBJ[ 'From' ] = SMTP_FROM
MESSAGE_OBJ[ 'To' ] = SMTP_TO

LOSS_COUNT = 0
GAIN_COUNT = 0

def check_log_dir():
    if os.path.exists( LOG_PATH ):
        return

    try:
        os.makedirs( LOG_PATH )
    except OSError:
        raise # TODO: disable logging?

def init_logging():
    # declare and add rotating file handler only if logging is enabled
    if LOG_ENABLE:
        handler = logging.handlers.RotatingFileHandler( filename=LOG_FULLPATH, maxBytes=(1024*1024)*LOG_MAXSIZE, backupCount=10 )
        handler.setFormatter( LOG_FORMAT )
        LOGGER.addHandler( handler )

    print_handler = logging.StreamHandler( stream=sys.stdout )
    print_handler.setFormatter( LOG_FORMAT )
    LOGGER.addHandler( print_handler )
    LOGGER.setLevel( logging.INFO )

def load_email_content():
    env = Environment( loader=FileSystemLoader( PWD_PATH ), trim_blocks=True )
    msg = env.get_template( EMAIL_TMPL_FILENAME ).render()
    MESSAGE_OBJ.attach( MIMEText( msg, 'html', 'utf-8' ) )

def send_email():
    try:
        smtp_obj = smtplib.SMTP( SMTP_HOST, SMTP_PORT )
        smtp_obj.starttls()
        smtp_obj.login( SMTP_USER, SMTP_PASS )
        smtp_obj.sendmail( SMTP_FROM, SMTP_TO, MESSAGE_OBJ.as_string() )
        smtp_obj.quit()

        print( Fore.GREEN + 'Successfully sent email.' + Style.RESET_ALL )
    except smtplib.SMTPException:
        print( Fore.RED + 'ERROR: Unable to send email!' + Style.RESET_ALL )

def handle_moisture_gain( value ):
    global GAIN_COUNT # pylint: disable=W0603
    GAIN_COUNT += 1
    LOGGER.info(
        Fore.YELLOW + 'Moisture gain detected! (#' + str( GAIN_COUNT ) + ')' +
        Style.RESET_ALL
    )
    LOGGER.info(
        'Value: ' + Style.BRIGHT + str( value ) +
        Style.RESET_ALL
    )

def handle_moisture_loss( value ):
    global LOSS_COUNT # pylint: disable=W0603
    LOSS_COUNT += 1
    LOGGER.info(
        Fore.CYAN + 'Moisture loss detected! (#' + str( LOSS_COUNT ) + ')' +
        Style.RESET_ALL
    )
    LOGGER.info(
        'Value: ' + Style.BRIGHT + str( value ) +
        Style.RESET_ALL
    )
    # load_email_content()
    # send_email()

try:
    check_log_dir()
    init_logging()

    # monitor moisture level logic
    MOISTURE_SENSOR = SDIMoistureSensor()
    MOISTURE_SENSOR.on_moisture_gain = handle_moisture_gain
    MOISTURE_SENSOR.on_moisture_loss = handle_moisture_loss
    MOISTURE_SENSOR.run()
except ( KeyboardInterrupt, EOFError ):
    pass
finally:
    LOGGER.info( Fore.GREEN + 'Exiting...' + Style.RESET_ALL )

import board
import busio
import RPi.GPIO as GPIO
from digitalio import DigitalInOut
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import sh1106
from adafruit_pn532.i2c import PN532_I2C
import time
from datetime import datetime, date
import json
import requests
import numpy as np
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

# DB
db = "https://embedded-systems-cf93d-default-rtdb.europe-west1.firebasedatabase.app/"

# Define the private key file (change to use your private key)
keyfile = "/home/pi/python/embedded-systems-cf93d-firebase-adminsdk-amky8-e0a50b80ba.json"

# Define the required scopes
scopes = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/firebase.database"
]

# Authenticate a credential with the service account (change to use your private key)
credentials = service_account.Credentials.from_service_account_file(keyfile, scopes=scopes)

# Use the credentials object to authenticate a Requests session.
authed_session = AuthorizedSession(credentials)

# Add RFID
def rfiduserinout(card, inout):
    date_today = date.today()
    path = f"rfidcards/{card}/{date_today}.json"

    read = authed_session.get(db + path)

    if read.json() is not None:
        data = read.json()
    else:
        data = {}
    if inout == "in":
        print(datetime.now().strftime("%H:%M:%S"))
        data["In"] = datetime.now().strftime("%H:%M:%S")

    else:
        data["Out"] = datetime.now().strftime("%H:%M:%S")
    
    resp = authed_session.put(db + path, json=data)

    if resp.ok:
        print("Ok")
    else:
        print(resp)
        raise

# LEDs
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(27,GPIO.OUT)
GPIO.setup(17,GPIO.OUT)
red_led = 17
green_led = 27
high = GPIO.HIGH
low = GPIO.LOW

# RFID
i2cRFID = busio.I2C(board.SCL, board.SDA)
reset_pin = DigitalInOut(board.D6)
req_pin = DigitalInOut(board.D12)
pn532 = PN532_I2C(i2cRFID, debug=False, reset=reset_pin, req=req_pin)


# Configure PN532 to communicate with MiFare cards
pn532.SAM_configuration()


# Display
serial = i2c(port=1, address=0x3C)
device = sh1106(serial, rotate=0)

title1 = 'Welcome!'
title2 = 'Please scan ID...'
title3 = 'ACCEPTED'
title4 = 'PROCEED'
titleIN = 'Status: IN'

UID_title = 'ID: '

def led(colour, status):
    GPIO.output(colour, status)

def checkSignIn(uid):
    # Checks if signing in / out
    with open('status.txt', 'r') as file:
        content = file.read()
        file.close()
    
    # If ID already signed in, remove ID from status.txt
    if uid in content:
        print('Signed Out')
        new_content = content.replace(uid, '')
        with open('status.txt', 'w') as file:
            file.write(new_content)
            file.close()
        return False
    # Else add ID too status.txt
    else:
        print('Signed In')
        with open('status.txt', 'a') as file:
            file.write(uid)
            file.close()
        return True

def main():

    with open('status.txt', 'w') as f:
        pass
        
    print("Waiting for RFID/NFC card...")
    
    statusFile = open('status.txt', 'a')
    
    led(red_led, high)
    
    while True:
        now = datetime.now().strftime("%H:%M")
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((90, 8), now, fill="white")
            draw.text((10, 20), title1, fill="white")
            draw.text((10, 30), title2 , fill="white")
            
        # Check if a card is available to read
        uid = pn532.read_passive_target(timeout=0.5)
        
        # Try again if no card is available.
        if uid is None:
            continue
        
        # If card is detected:
        # Set Green LED ON and Red LED OFF
        led(green_led, high)
        led(red_led, low)
        
        # Convert User ID into string format
        uid = [hex(i) for i in uid]
        uid_string = ''.join(format(int(i, 16), '02x') for i in uid)
        print("UID:", uid_string)
        
        # Accepted Display
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((90, 8), now, fill="white")
            draw.text((40, 25), title3, fill="white")
        time.sleep(0.5)
        
        # Accepted + Proceed Display
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((90, 8), now, fill="white")
            draw.text((40, 25), title3, fill="white")
            draw.text((44, 35), title4, fill="white")
        time.sleep(1)
        
        # Checks Status IN/OUT
        if checkSignIn(uid_string) == True:
            titleIN = "Status: IN"
            rfiduserinout(uid_string, "in")
        else:
            titleIN = "Status: OUT"
            rfiduserinout(uid_string, "out")
        
        # Status IN/OUT Displayed
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((90, 8), now, fill="white")
            draw.text((33, 30), titleIN , fill="white")
        time.sleep(2)
        led(green_led, low)
        led(red_led, high)
main()

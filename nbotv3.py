import requests
import json
from twilio.rest import Client
import time as system_time
from datetime import datetime
from datetime import time
import re

URL_Direct = "https://api-prod.nvidia.com/direct-sales-shop/DR/products/en_gn/GBP/5438792800"

seconds_between_checks = 3

times_to_report_operation = [
    time(8, 0, 0, 0),
    time(10, 0, 0, 0),
    time(12, 0, 0, 0),
    time(12, 55, 0, 0),
    time(13, 30, 0, 0),
    time(15, 30, 0, 0),
    time(18, 0, 0, 0),
    time(21, 47, 0, 0)
]

direct_link_regex = re.compile('.*"productIsInStock": "false"', flags=re.IGNORECASE)

twilio_account_sid = 'ADD'
twilio_auth_token = 'ADD'
twilio_source_phone_number = 'ADD'
twilio_target_phone_number = 'ADD'

def IsStillOutOfStock():
    req = requests.get(URL_Direct)
    if req.ok:
        return direct_link_regex.search(req.text) != None
    return True

def SendSmsMessage(message):
    print("Sending SMS: " + message)
    client = Client(twilio_account_sid, twilio_auth_token)
    client.messages.create(
        body=message,
        from_=twilio_source_phone_number,
        to=twilio_target_phone_number
    )

# Program Entry:

if IsStillOutOfStock() == True:
    SendSmsMessage("NVIDIA Monitor set up Successful!")
else:
    SendSmsMessage("Monitor set up not successful (or item is in stock), could not confirm item is out of stock -> Program has terminated")
    quit()

time_of_last_check = datetime.utcnow()

loop = True

while loop:
    if IsStillOutOfStock() == False:
        SendSmsMessage("ALERT: Item appears to be back in stock!!! Time is: " + datetime.now().strftime("%H:%M:%S"))
        quit()

    time_of_current_check = datetime.utcnow()

    last_utc = time_of_last_check.time()
    now_utc = time_of_current_check.time()

    for t in times_to_report_operation:
        if last_utc < t and now_utc >= t:
            SendSmsMessage("NVIDIA bot reporting in - all systems OK!")

    time_of_last_check = time_of_current_check

    system_time.sleep(seconds_between_checks)

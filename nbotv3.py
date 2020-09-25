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
direct_link_regex_2 = re.compile('.*"status": "PRODUCT_INVENTORY_OUT_OF_STOCK"', flags=re.IGNORECASE)

twilio_account_sid = 'ADD'
twilio_auth_token = 'ADD'
twilio_source_phone_number = 'ADD'
twilio_target_phone_number = 'ADD'

def IsStillOutOfStock():
    req = requests.get(URL_Direct)
    obj = json.loads(req.text)
    
    if req.ok:
        try:
            status = obj['products']['product'][0]['inventoryStatus']
            return status['productIsInStock'] == 'false' and status['status'] == 'PRODUCT_INVENTORY_OUT_OF_STOCK'
        #return ((direct_link_regex.search(req.text) != None) or (direct_link_regex_2.search(req.text) != None))
        except:
            return True
    return True

def SendSmsMessage(message):
    print("Sending SMS: " + message)
    client = Client(twilio_account_sid, twilio_auth_token)
    client.messages.create(
        body=message,
        from_=twilio_source_phone_number,
        to=twilio_target_phone_number
    )

def stock_string(out_of_stock):
    if out_of_stock == True:
        return "out of stock"
    else:
        return "IN STOCK"

# Program Entry:

out_of_stock = IsStillOutOfStock()

SendSmsMessage("NVIDIA Monitor set up: Initial State: " + str(stock_string(out_of_stock)) + " -> at " + datetime.now().strftime("%H:%M:%S"))

time_of_last_check = datetime.utcnow()

loop = True

while loop:
    new_out_of_stock = IsStillOutOfStock()

    if new_out_of_stock != out_of_stock:
        out_of_stock = new_out_of_stock
        SendSmsMessage("ALERT: " + str(stock_string(out_of_stock)) + " -> at "+ datetime.now().strftime("%H:%M:%S"))

    time_of_current_check = datetime.utcnow()

    last_utc = time_of_last_check.time()
    now_utc = time_of_current_check.time()

    for t in times_to_report_operation:
        if last_utc < t and now_utc >= t:
            SendSmsMessage("NVIDIA bot reporting in - all systems OK!")

    time_of_last_check = time_of_current_check

    system_time.sleep(seconds_between_checks)

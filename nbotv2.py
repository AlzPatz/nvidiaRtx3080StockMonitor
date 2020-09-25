from bs4 import BeautifulSoup
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client
import time as system_time
from datetime import datetime
from datetime import time
import re

URL_FilteredShop = "https://www.nvidia.com/en-gb/shop/geforce/gpu/?page=1&limit=9&locale=en-gb&gpu=RTX%203080&category=GPU&manufacturer=NVIDIA&manufacturer_filter=NVIDIA~1,ASUS~0,EVGA~0,GAINWARD~0,GIGABYTE~0,MSI~0,PALIT~2,PNY~0,ZOTAC~0"

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

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

rtx_regex = re.compile('.*RTX 3080.*', flags=re.IGNORECASE)
out_of_stock_regex = re.compile('.*out.of.stock.*', flags=re.IGNORECASE)
check_availability_regex = re.compile('.*check.availability.*', flags=re.IGNORECASE)

out_of_stock_search_failure_count = 0
search_failure_report_threshold = 4

twilio_account_sid = 'REMOVED'
twilio_auth_token = 'REMOVED'
twilio_source_phone_number = 'REMOVED'
twilio_target_phone_number = 'REMOVED'


def IsStillOutOfStock():
    global out_of_stock_search_failure_count

    with Chrome(options=chrome_options) as browser:
        browser.get(URL_FilteredShop)
        html = browser.page_source

    soup = BeautifulSoup(html, 'html.parser')

    #Seach for Featured Container
    potential_matches_featured = soup.find_all('div', attrs={'class' : re.compile('featured-container.*')})
    potential_matches_product = soup.find_all('div', attrs={'class' : re.compile('product-details-container.*')})

    #If no containers found, let's assume a bad page load, but err on side of caution, so do not trigger
    #We add to a count however, too many fails in a row should be a manual check
    if len(potential_matches_product) + len(potential_matches_featured) == 0:
        out_of_stock_search_failure_count = out_of_stock_search_failure_count + 1
        return True

    rtx_3080_found = False
    out_of_stock_found = False

    for container in potential_matches_featured:
        if rtx_regex.search(container.text) != None:
            rtx_3080_found = True
            if (out_of_stock_regex.search(container.text) != None) or (check_availability_regex.search(container.text) != None):
                out_of_stock_found = True

    for container in potential_matches_product:
        if rtx_regex.search(container.text) != None:
            rtx_3080_found = True
            if (out_of_stock_regex.search(container.text) != None) or (check_availability_regex.search(container.text) != None):
                out_of_stock_found = True

    if rtx_3080_found:
        return out_of_stock_found
    else:
        out_of_stock_search_failure_count = out_of_stock_search_failure_count + 1
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

def stock_string(out_of_stock):
    if out_of_stock == True:
        return "out of stock"
    else:
        return "IN STOCK"

def SendMessage(out_of_stock):
    SendSmsMessage("ALERT SCRAPER: " + str(stock_string(out_of_stock)) + " -> at "+ datetime.now().strftime("%H:%M:%S"))

def IsOutOfHours():
    now = datetime.utcnow().time()
    return  now < time(7, 0, 0, 0) or now >= time(22, 0, 0, 0)

# Program Entry:

out_of_stock = IsStillOutOfStock()

SendSmsMessage("NVIDIA SCRAPER set up: Initial State: " + str(stock_string(out_of_stock)) + " -> at " + datetime.now().strftime("%H:%M:%S"))

time_of_last_check = datetime.utcnow()

loop = True

has_sent_one_message_out_of_hours = False

while loop:
    new_out_of_stock = IsStillOutOfStock()
    # Double Check 
    if new_out_of_stock == False:
         new_out_of_stock = IsStillOutOfStock()

    if new_out_of_stock != out_of_stock:
        out_of_stock = new_out_of_stock
        if IsOutOfHours() == True:
            if has_sent_one_message_out_of_hours == False:
                has_sent_one_message_out_of_hours = True
                SendSmsMessage("SCRAPER: As it is out of hours, will supress any further messages until morning")
                SendMessage(out_of_stock)
        else:
            has_sent_one_message_out_of_hours = False
            SendMessage(out_of_stock)

    time_of_current_check = datetime.utcnow()

    last_utc = time_of_last_check.time()
    now_utc = time_of_current_check.time()

    for t in times_to_report_operation:
        if last_utc < t and now_utc >= t:
            SendSmsMessage("NVIDIA bot reporting in - all systems OK! State: " + str(stock_string(out_of_stock)) + " -> at " + datetime.now().strftime("%H:%M:%S"))

    time_of_last_check = time_of_current_check

    system_time.sleep(seconds_between_checks)

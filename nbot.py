from bs4 import BeautifulSoup
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from twilio.rest import Client
import time as system_time
from datetime import datetime
from datetime import time
import re

URL_FilteredShop = "https://www.nvidia.com/en-gb/shop/geforce/gpu/?page=1&limit=9&locale=en-gb&gpu=RTX%203080&category=GPU&manufacturer=NVIDIA&manufacturer_filter=NVIDIA~1,ASUS~0,EVGA~0,GAINWARD~0,GIGABYTE~0,MSI~0,PALIT~2,PNY~0,ZOTAC~0"

seconds_between_checks = 10

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

out_of_stock_search_failure_count = 0
search_failure_report_threshold = 3

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
    potential_matches = soup.find_all('div', attrs={'class' : re.compile('featured-container.*')})

    #If no containers found, let's assume a bad page load, but err on side of caution, so do not trigger
    #We add to a count however, too many fails in a row should be a manual check
    if len(potential_matches) == 0:
        out_of_stock_search_failure_count = out_of_stock_search_failure_count + 1
        return True

    for container in potential_matches:
        #Search for tags containing product names
        product_names = container.find_all('h2', attrs={'class' : 'name'})

        #If none found, again err on the side of caution
        if len(product_names) == 0:
            out_of_stock_search_failure_count = out_of_stock_search_failure_count + 1
            return True

        rtx_3080_found = False
        for name in product_names:
            if rtx_regex.search(name.text) != None:
                rtx_3080_found = True
                buy_links = container.find_all('a', attrs={ 'class' : re.compile('featured-buy-link.*')})
                out_of_stock_found = False
                for link in buy_links:
                    if out_of_stock_regex.search(link.text) != None:
                        out_of_stock_found = True
        
        #If RTX 3080 product is not found, err on the side of caution again, but update failure count
        if rtx_3080_found == False:
            out_of_stock_search_failure_count = out_of_stock_search_failure_count + 1
            return True
        
        #We found the product, now we can return whether out of stock was found or not
        return out_of_stock_found

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
    
    if out_of_stock_search_failure_count >= search_failure_report_threshold:
        SendSmsMessage("WARNING: Search has failed to confirm out of stock " + str(out_of_stock_search_failure_count) + " times, please check website")
        out_of_stock_search_failure_count = 0

    time_of_current_check = datetime.utcnow()

    last_utc = time_of_last_check.time()
    now_utc = time_of_current_check.time()

    for t in times_to_report_operation:
        if last_utc < t and now_utc >= t:
            SendSmsMessage("NVIDIA bot reporting in - all systems OK!")

    time_of_last_check = time_of_current_check

    system_time.sleep(seconds_between_checks)

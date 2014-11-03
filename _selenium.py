from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep
import sys

def checkout(selenium):
    noc = selenium.find_element_by_xpath('//input[@ng-model="payment.name"]')
    noc.clear()
    noc.send_keys('Jonathan Consumer')
    cc = selenium.find_element_by_xpath('//input[@ng-model="payment.number"]')
    cc.clear()
    cc.send_keys('4242424242424242')
    mm = selenium.find_element_by_xpath('//input[@ng-model="payment.exp_month"]')
    mm.clear()
    mm.send_keys('12')
    yyyy = selenium.find_element_by_xpath('//input[@ng-model="payment.exp_year"]')
    yyyy.clear()
    yyyy.send_keys('2020')
    cvc = selenium.find_element_by_xpath('//input[@ng-model="payment.cvc"]')
    cvc.clear()
    cvc.send_keys('123')
    sleep(1)
    selenium.find_element_by_xpath('//input[@type="checkbox"]').click()
    selenium.find_element_by_xpath('//button[@ng-click="cc_on_file=true"]')

if __name__ == "__main__":
    url = 'http://localhost:8082/'
    useremail = 'selenium@test.com'
    if len(sys.argv) > 1:
        url = str(sys.argv[1])
    print("URL: " + url)
    if len(sys.argv) > 2:
        useremail = str(sys.argv[2])
    print("Email: " + useremail)

    selenium = WebDriver()
    selenium.maximize_window()
    selenium.get(url)
    selenium.find_element_by_name('signup_btn').click()
    sleep(2)
    biz = selenium.find_element_by_xpath('//input[@ng-model="biz"]')
    biz.send_keys('Sushi')
    zipc = selenium.find_element_by_xpath('//input[@ng-model="loc"]')
    zipc.send_keys('90041')
    sleep(1)
    selenium.find_element_by_name('find me').click()
    sleep(1)
    selenium.find_element_by_name('find me').click()
    sleep(3)
    selenium.find_element_by_xpath('//button[@class="btn  btn-woo btn-large open-bold small-font round_corners"]').click()
    sleep(4)
    selenium.find_element_by_xpath('//a[@ng-click="go_on()"]').click()
    sleep(3)
    name = selenium.find_element_by_id('first_name')
    name.send_keys('Selenium User')
    email = selenium.find_element_by_xpath('//input[@type="email"]')
    email.send_keys(useremail)
    pw = selenium.find_element_by_xpath('//input[@ng-model="advertiser.password"]')
    pw.send_keys('testtest')
    pw2 = selenium.find_element_by_xpath('//input[@ng-model="confirm_password"]')
    pw2.send_keys('testtest')
    selenium.find_element_by_xpath('//input[@type="checkbox"]').click()
    selenium.find_element_by_xpath('//button[@analytics-event="create_acct"]').click()
    sleep(1)
    try:
        campname = selenium.find_element_by_xpath('//input[@name="campaign_name_inp"]')
        campname.send_keys('Selenium Test')
        selenium.find_element_by_id('go_on_btn').click()
    except:
        sleep(3)
        # campname = selenium.find_element_by_xpath('//input[@name="campaign_name_inp"]')
        # campname.send_keys('Selenium Test')
        selenium.find_element_by_id('go_on_btn').click()
    sleep(1)
    try:
        selenium.find_element_by_xpath('//button[@ng-click="save_go_on()"]').click()
    except:
        sleep(3)
        selenium.find_element_by_xpath('//button[@ng-click="save_go_on()"]').click()
    sleep(3)
    try:
        print("Let's try this")
        selenium.find_element_by_xpath('//button[@ng-click="save_go_on()"]').click()
    except:
        print("One more time")
        sleep(4)
        selenium.find_element_by_xpath('//button[@ng-click="save_go_on()"]').click()
    sleep(4)
    try:
        sleep(2)
        ph = selenium.find_element_by_xpath('//input[@ng-model="yelp.yelp_data.banner_actions.call.value"]')
        ph.send_keys('555-444-3232')
        button = selenium.find_element_by_xpath('//button[@analytics-event="goto_targeting"]')
        button.click()
    except:
        sleep(4)
        ph = selenium.find_element_by_xpath('//input[@ng-model="yelp.yelp_data.banner_actions.call.value"]')
        ph.send_keys('555-444-3232')
        button = selenium.find_element_by_xpath('//button[@analytics-event="goto_targeting"]')
        button.click()
    try:
        sleep(2)
        selenium.find_element_by_xpath('//button[@ng-click="save_go_on()"]').click()
    except:
        sleep(5)
        selenium.find_element_by_xpath('//a[@ng-class="{true:\'current\', false:\'\'}[obj.page_name == \'targeting\']"]').click()
    try:
        sleep(1)
        selenium.find_element_by_xpath('//button[@ng-click="save_go_to_checkout()"]').click()
    except:
        sleep(4)
        selenium.find_element_by_xpath('//button[@ng-click="save_go_to_checkout()"]').click()

    # checking out
    if len(sys.argv) > 3:
        if str(sys.argv[3]) == "checkout":
            sleep(2)
            try:
                checkout(selenium)
            except:
                sleep(5)
                checkout(selenium)


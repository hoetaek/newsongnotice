from selenium import webdriver
import time
import random


def close_popup(driver):
    parent_h = driver.current_window_handle
    # click on the link that opens a new window
    handles = driver.window_handles # before the pop-up window closes
    handles.remove(parent_h)
    driver.switch_to.window(handles.pop())
    driver.find_element_by_css_selector('div.tmp-footer > button').click()
    # popup window closes
    driver.switch_to.window(parent_h)
    # and you're back
    return driver


def vote(usr, pw, url):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    options.add_argument('window-size=1920x1080')
    options.add_argument("disable-gpu")
    options.add_argument("--disable-notifications")
    driver = webdriver.Chrome('chromedriver', options=options)
    driver.get('https://www.teacherville.co.kr/portal/memship/loginSSL.edu')
    driver.find_element_by_css_selector('#id').send_keys(usr)
    driver.find_element_by_css_selector('#pw').send_keys(pw)
    driver.find_element_by_css_selector('#btn-login').click()
    time.sleep(3)
    try:
        driver = close_popup(driver)
    except IndexError:
        time.sleep(3)
        try:
            driver = close_popup(driver)
        except IndexError:
            time.sleep(3)
            try:
                driver = close_popup(driver)
            except IndexError:
                time.sleep(3)
                try:
                    driver = close_popup(driver)
                except IndexError:
                    driver = close_popup(driver)
    driver.get(url)
    time.sleep(4)
    driver.find_element_by_css_selector('#page-wrapper > div > div.event03 > div > div.list_cont > div > button > p').click()
    driver.quit()


def start_voting(users):
    for i, user in enumerate(users, start=1):
        usr, pw = user
        print(i, usr, pw)
        vote(usr, pw, 'https://ssam.teacherville.co.kr/?mode=event.schoolstarts&sub=teacher&keyword=울독송')
        time.sleep(random.randint(2, 10))
        vote(usr, pw, 'https://ssam.teacherville.co.kr/?mode=event.schoolstarts&sub=teacher&keyword=흥딩스쿨')
        time.sleep(random.randint(2, 10))
        vote(usr, pw, 'https://ssam.teacherville.co.kr/?mode=event.schoolstarts&sub=teacher&keyword=교사에대하여')
        time.sleep(random.randint(2, 10))
        if i % 3 == 0:
            t = random.randint(300, 600)
            print(time.localtime())
            print(f"{t//60}분 동안 쉬어갑니다~")
            time.sleep(t)

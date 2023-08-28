import asyncio
import os
import pickle
import time
import traceback
from datetime import datetime
from threading import Event, current_thread

from fake_useragent import FakeUserAgent
from selenium.common import NoSuchElementException
from selenium.webdriver import Chrome as BrowserDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from src.core.decorators.io import q, async_io_action
from src.core.types.match import MatchItem


class SeleniumBase:
    driver_browser = None
    _cookies: list[dict]
    _event: Event

    def __init__(self,
                 path_driver: str,
                 event: Event,
                 browser_type: str = 'chrome',
                 **options_browser: dict[str, str]):
        self._event = event

        service = Service(executable_path=path_driver)
        options = Options()
        ua = FakeUserAgent().random

        # options.add_argument(f'user-agent={ua}')
        # options.add_argument('--disable-gpu')
        # options.add_argument('--no-sandbox')
        # options.add_argument('--disable-dev-shm-usage')
        # options.add_experimental_option("detach", True)
        if options_browser:
            for option_name, option_value in options_browser.items():
                options.add_argument(f'{option_name}={option_value}')

        driver_browser = BrowserDriver(options=options, service=service)
        driver_browser.set_window_size(1360, 740)
        driver_browser.set_window_position(570, 27)
        self.driver_browser = driver_browser

    @property
    def get_cookies(self):
        return self.driver_browser.get_cookies()

    async def authorization_pari(self, login: str, password: str):
        driver = self.driver_browser
        try:
            driver.get("https://www.pari.ru/account/")

            driver.implicitly_wait(5)

            login_xpath = '//form/div[2]//input'
            login_input = driver.find_element(By.XPATH, login_xpath)
            login_input.clear()
            login_input.send_keys(login)

            password_xpath = '//form/div[3]//input'
            password_input = driver.find_element(By.XPATH, password_xpath)
            password_input.clear()
            password_input.send_keys(password)

            enter_btn_xpath = '//form/div[5]//button'
            driver.find_element(By.XPATH, enter_btn_xpath).click()
            account_balance_xpath = '//span[contains(text(), "Баланс")]'
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH, account_balance_xpath
                ))
            )

        except NoSuchElementException as exc:
            if exc.msg.count('Unable to locate element'):
                return await self.authorization_pari(
                    login=login,
                    password=password
                )
            raise exc

        except Exception:
            print(traceback.format_exc())

    async def select_and_go_to_sport_page(self,
                                          sport: str,
                                          type_sport: str):

        sports_modes = {
            'live': 'https://www.pari.ru/live',
            'sports': 'https://www.pari.ru/sports',
            "mode_1": 'https://www.pari.ru/sports/?mode=1',
        }
        assert type_sport in list(sports_modes.keys())

        driver = self.driver_browser
        try:
            url = sports_modes[type_sport]
            driver.get(url)
            from selenium.webdriver.support import expected_conditions as ec

            sport_xpath = f'//span[contains(text(), "{sport}")]'
            WebDriverWait(driver, 30).until(
                ec.element_to_be_clickable((By.XPATH, sport_xpath)))

            sport_section = driver.find_element(By.XPATH, sport_xpath)
            sport_section.click()

        except Exception:
            print(traceback.format_exc())

    async def follow_the_match(self):
        driver = self.driver_browser
        self._event.set()
        self._event.clear()

        while True:

            await asyncio.sleep(3)

            if q.qsize() > 0:
                data = q.get()
                bet = data[0]
                item: MatchItem = data[1]

                driver.get(item.view_url.replace('fon.bet', 'pari.ru'))

                part = f"{item.part}-я четверть"
                if item.part >= 4:
                    part = 'Матч'

                if bet.count('нечет'):
                    div_num = 3
                else:
                    div_num = 2

                part_btn_xpath = f'//div[@class = "menu--5VDF7U"]//div[text() = "{part}"]'
                driver.implicitly_wait(10)
                part_btn = driver.find_element(By.XPATH, part_btn_xpath)
                part_btn.click()
                driver.implicitly_wait(5)
                bet_button_xpath = ('//div[text()="Тотал чет"]/../../../'
                                    f'div[{div_num}]')
                try:
                    bet_btn = driver.find_element(By.XPATH, bet_button_xpath)
                    driver.implicitly_wait(10)
                    bet_btn.click()
                except NoSuchElementException:
                    print('Закончилось принятие ставок по росписи. ')
                    date_time = '-'.join(datetime.now().ctime().split()).lower()
                    driver.save_screenshot(f'src/selenium/{date_time}.png')

                else:
                    input_sum_xpath = '//input[@placeholder="Введи сумму"]'
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,
                                                       input_sum_xpath))
                    )

                    input_sum = driver.find_element(By.XPATH, input_sum_xpath)
                    input_sum.clear()
                    input_sum.send_keys('30')

                    do_bet_btn_xpath = '//div[contains(text(), "Заключить пари")]'
                    do_bet_btn = driver.find_element(By.XPATH, do_bet_btn_xpath)
                    print('Я бы поставил, но не могу')
                    th = current_thread()
                    with open('bets.txt', 'a') as f:
                        text = (f'[{th.name}] Ставка {bet}, на {part} матча '
                                f'{item.teams}. Время - '
                                f'{datetime.now().strftime("%d.%m - %H:%M:%S")}\n')
                        f.write(text)
                    # do_bet_btn.click()


@async_io_action
async def selenium_main(event: Event):
    driver_path = ('/home/daniil/PycharmProjects/new_better/src/selenium'
                   '/chromedriver')
    selenium = SeleniumBase(path_driver=driver_path, event=event)
    cookie_path = 'src/core/utils/cookies.pkl'

    with open(cookie_path, 'rb') as f:
        if os.stat(cookie_path).st_size != 0:
            await selenium.select_and_go_to_sport_page(
                'Баскетбол', type_sport='live'
            )

            cookies = pickle.load(open(cookie_path, "rb"))
            for cookie in cookies:
                selenium.driver_browser.add_cookie(cookie)

            selenium.driver_browser.refresh()
            time.sleep(5)

        else:
            login = '89859829232'
            password = '132671BDDT'
            await selenium.authorization_pari(login, password)
            await selenium.select_and_go_to_sport_page(
                'Баскетбол', type_sport='live'
            )
            pickle.dump(
                selenium.driver_browser.get_cookies(),
                open(cookie_path, "wb")
            )

    event.set()
    event.clear()

    await selenium.follow_the_match()


if __name__ == '__main__':
    asyncio.run(selenium_main(''))

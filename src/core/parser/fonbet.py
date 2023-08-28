import asyncio
import logging
import random
from datetime import datetime
from json import JSONDecodeError
from threading import Event, current_thread

from aiohttp import ClientSession

from src.core.decorators.counter import GuessCounter
from src.core.decorators.io import q, async_io_action
from src.core.decorators.parsing import aiohttp_timeout_reciever
from src.core.exceptions.guess import GuessNotification
from src.core.types.match import MatchItem

logging.getLogger('asyncio').setLevel(logging.CRITICAL)


class FonbetCollector:
    _url_all_data: str = 'https://line52w.bk6bba-resources.com/events/list?' \
                         'lang=ru&version=0&scopeMarket=1600'
    _data_bookmaker: dict
    _data_url_item_from_bookmaker: str
    max_counter: int = 9
    _counter: int = 0
    bet: str
    test: bool
    _previos_part: int = None
    _guess: str = None
    _previos_score: dict
    _item: MatchItem
    _event: Event

    def __init__(self, event: Event):
        self._event = event
        self.set_bet()

    def set_bet(self):
        bets = ['ЧЕТ', "НЕЧЕТ"]
        self.bet = random.choice(bets)

    @aiohttp_timeout_reciever()
    async def get_sports(self,
                         session: ClientSession,
                         sportname: str,
                         liganame: str = None) -> list:
        """
        Получает список спортов по фильтру
        :param session:
        :type session:
        :param sportname: Имя спорта
        :param liganame: Имя лиги (по желанию)
        :return: Список собранных спортов
        """

        async with session.get(url=self._url_all_data) as response:
            data = await response.json()
            self._data_bookmaker = data

        sports = [
            {"id": sport["id"], "name": sport["name"]}
            for sport in data["sports"]
            if sport["name"].lower().count(sportname.lower()) and
               sport["name"].lower().startswith(f'{sportname}.')
        ]

        if liganame is not None:
            return [
                sport
                for sport in sports
                if sport["name"].lower().count(liganame.lower())
            ]
        else:
            [
                sports.remove(sport["name"])
                for sport in sports
                if sport["name"].lower() == sportname.lower() + '.'
            ]
            return sports

    async def get_items(self,
                        sports: list,
                        max_time: list[int, int] | None = None) -> list[dict]:
        """
        Получить список игр на фонбете
        """

        data = self._data_bookmaker

        items = [
            item
            for item in data["events"]
            for sport in sports
            if sport["id"] == item['sportId'] and
               item["level"] == 1
        ]

        def build_url(score_function: str,
                      sport_id: str | int,
                      item_id: str | int):
            url = f'https://fon.bet/live/{score_function.lower()}/'
            return f"{url}{sport_id}/{item_id}"

        def build_item_share_url(item_id: int | str):
            return (f'https://line32w.bk6bba-resources.com/events/'
                    f'event?lang=ru&eventId={item_id}')

        def build_item_info(live_item_info: dict,
                            item_info: dict) -> dict:
            return {
                "view_url": build_url(live_item_info['scoreFunction'],
                                      item_info["sportId"],
                                      item_info["id"]),
                "data_url": build_item_share_url(item_info["id"]),
                "live_time": (live_item_info['timer'] if
                              live_item_info.get('timer') else
                              'Матч не начался'),
                "teams_names": [item_info['team1'], item_info['team2']],
                'liganame': [
                    sport["name"]
                    for sport in sports
                    if sport['id'] == item_info['sportId']
                ]
            }

        items_data = []
        for live_item in data['liveEventInfos']:
            for item in items:
                if live_item['eventId'] == item['id']:

                    if live_item.get('timer'):
                        if max_time:
                            item_time = [int(live_item['timer'].split(':')[0]),
                                         int(live_item['timer'].split(':')[1])]
                            if item_time[0] > max_time[0]:
                                continue
                            elif item_time[0] == max_time[0]:
                                if item_time[1] > max_time[1]:
                                    continue

                    items_data.append(build_item_info(live_item, item))

        return items_data

    @aiohttp_timeout_reciever(timeout=1)
    async def collect_and_get_data_item(self,
                                        session: ClientSession,
                                        url: str,
                                        max_part: int,
                                        view_url: str) -> MatchItem:
        async with session.get(url=url) as response:
            try:
                data = await response.json(content_type=None)
            except (JSONDecodeError, UnicodeDecodeError):
                await asyncio.sleep(1)
                return await self.collect_and_get_data_item(
                    url=url,
                    max_part=max_part,
                    view_url=view_url
                )
            if not data.get('liveEventInfos'):
                self.check_bet(item=self._item)
                raise AssertionError

            live_item_info = data['liveEventInfos'][0]
            item_info = data['events'][0]
            sport_info = data['sports'][1]

        team1, team2 = item_info["team1"], item_info["team2"]
        sportname = sport_info['name']

        timer = (live_item_info['timer'] if live_item_info.get('timer')
                 else 'Матч не начался')

        if len(live_item_info['scores']) > 1:
            part = len(live_item_info['scores'][1])
        else:
            part = 1

        if not self._previos_part:
            self._previos_part = part

        general_score = live_item_info['scores'][0][0]

        if part == 1:
            score_previos = general_score
        else:
            score_previos = live_item_info['scores'][1][part - 2]

        self._previos_score = score_previos

        if part == 1:
            score = general_score
        elif part < max_part:
            score = live_item_info['scores'][1][part - 1]
        else:
            score = general_score

        item = MatchItem(timer=timer, teams=[team1, team2],
                         sportname=sportname, part=part, score=score,
                         general_score=general_score,
                         previos_score=score_previos,
                         bet=self.bet,
                         view_url=view_url,
                         data_url=url)
        self._item = item

        # if item.part > self._previos_part:
        if self.test:
            self.test = False
            item.part = 4
            print(f'тест прошел {current_thread().name}')
            self.check_bet(item=item)

        self._previos_part = part
        return item

    def check_bet(self, item: MatchItem):
        success = GuessCounter().check_bet(self._previos_score, self.bet)

        if success:
            self._counter += 1
        else:
            self._counter = 0

        if self._counter >= self.max_counter:

            if self.bet.lower().startswith('ч'):
                q.put_nowait(['на нечет', item])
            else:
                q.put_nowait(['на чет', item])
            self._event.set()

        self.set_bet()


@async_io_action
async def start_work(event: Event, threadname: str):
    fonbet = FonbetCollector(event)
    await parse(fonbet=fonbet, threadname=threadname, event=event)


async def parse(fonbet: FonbetCollector, threadname: str, event: Event):
    max_time = [30, 30]
    sports = await fonbet.get_sports(sportname='баскетбол')
    items = await fonbet.get_items(sports=sports, max_time=max_time)

    if not items:
        print(f'Игр по заданным фильтрам не найдено, ищу все игры в спорте')
        sports = await fonbet.get_sports(sportname='баскетбол')
        items = await fonbet.get_items(sports=sports, max_time=max_time)

    item = random.choice(items)
    msg = (f'{datetime.now().ctime()}:  '
           f'Выбран матч: {item["teams_names"]}, '
           f'матч доступен по ссылке - {item["view_url"]}')
    print(msg)
    fonbet.max_counter = 0
    fonbet.test = True

    event.wait()
    while True:
        try:
            match = await fonbet.collect_and_get_data_item(
                item["data_url"], 4, view_url=item["view_url"]
            )
        except AssertionError:
            item = fonbet._item
            print(f'матч {item.teams} закончился', flush=True)
            return await parse(fonbet=fonbet, threadname=threadname)
        except GuessNotification:
            print(GuessNotification.default_message)

        else:
            match: MatchItem

            if isinstance(match.timer, str) and match.timer.count('не начался'):
                await asyncio.sleep(15)

        finally:
            await asyncio.sleep(1)

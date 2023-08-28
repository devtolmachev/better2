import asyncio
import logging
import random

from aiohttp import ClientSession

from src.core.decorators.parsing import aiohttp_timeout_reciever


logging.getLogger('asyncio').setLevel('CRITICAL')


class FonbetCollector2:
    _url_all_data: str = 'https://line52w.bk6bba-resources.com/events/list?' \
                         'lang=ru&version=0&scopeMarket=1600'
    _data_bookmaker: dict
    _data_url_item_from_bookmaker: str
    max_counter: int = 9
    _counter: int = 0
    bet: str
    _previos_part: int = None
    _guess: str = None

    def __init__(self, max_counter: int):
        self.set_bet()
        self.max_counter = max_counter

    def set_bet(self):
        bets = ['ЧЕТ', 'НЕЧЕТ']
        random_bet = random.choice(bets)
        self.bet = random_bet

    @aiohttp_timeout_reciever(timeout=1)
    async def get_sports(self,
                         session: ClientSession,
                         sportname: str,
                         liganame: str | None = None):
        url = self._url_all_data
        async with session.get(url=url) as response:
            data = await response.json(content_type=None)

        all_sports: list[dict] = [
            sport
            for sport in data["sports"]
            if not sport["kind"] == 'sport'
        ]

        needed_sports = []
        for sport in all_sports:

            if sport["name"].lower().count(sportname.lower()):

                if liganame:
                    if sport["name"].lower().count(liganame.lower()):
                        needed_sports.append(sport)
                    continue

                needed_sports.append(sport)

        return needed_sports

    @aiohttp_timeout_reciever(timeout=1)
    async def get_items(self,
                        session: ClientSession,
                        sports: list[dict] | None = None):
        url = self._url_all_data
        async with session.get(url=url) as response:
            data = await response.json(content_type=None)

        if not sports:
            return data["events"]
        else:
            sports_id = [
                sport["id"]
                for sport in sports
            ]
            return [
                item
                for item in data["events"]
                if item["sportId"] in sports_id
            ]

    async def get_live_items(self,
                             session: ClientSession,
                             sports: list[dict]):
        ...


async def main():
    fonbet = FonbetCollector2(3)
    sports = await fonbet.get_sports(sportname='баскетбол',
                                     liganame='nba 2k23')
    items = await fonbet.get_items(sports=None)
    print(sports, '\n\n')
    print(items, '\n\n')


if __name__ == '__main__':
    asyncio.run(main())

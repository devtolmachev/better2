from types import FunctionType

from src.core.decorators.io import q


def guessing_counter(func: FunctionType):
    async def wrapper(*args, **kwargs):
        data = await func(*args, **kwargs)

        bookmaker_collector = args[0]
        max_counter: int = bookmaker_collector.max_counter
        counter: int = bookmaker_collector._counter
        bet: str = bookmaker_collector.bet

        return data

    return wrapper


class GuessCounter:

    def check_bet(self, score: dict, bet: str) -> bool:
        if bet.lower() == 'чет':
            bet = 0
        elif bet.lower() == 'нечет':
            bet = 1
        else:
            raise NotImplementedError

        if (int(score['c1']) + int(score['c2'])) % 2 == 0:
            result = 0
        else:
            result = 1

        return bet == result

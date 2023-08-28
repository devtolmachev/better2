import asyncio
import random
from types import FunctionType

from aiohttp import ClientSession, ClientTimeout, TCPConnector, ClientConnectorError, ClientOSError
from fake_useragent import FakeUserAgent


def get_aiohttp_session(headers: dict = None,
                        timeout: int = None,
                        fake_ua: bool = True) -> ClientSession:
    if headers is None:
        headers = {}
    if fake_ua:
        ua = FakeUserAgent().random
        headers["User-Agent"] = ua

    connector = TCPConnector(limit_per_host=10, verify_ssl=False)
    if timeout:
        timeout = ClientTimeout(total=timeout)
        session = ClientSession(headers=headers,
                                timeout=timeout,
                                trust_env=True,
                                connector=connector)
    else:
        session = ClientSession(headers=headers,
                                trust_env=True,
                                connector=connector)

    return session


def aiohttp_timeout_reciever(timeout: int = None):
    def decorator(func: FunctionType):
        async def wrapper(*args, **kwargs) -> func:
            if len(args) < 2 or not isinstance(args[1], ClientSession):
                headers = {"Accept": "*/*"}
                session = get_aiohttp_session(headers=headers,
                                              timeout=timeout)

                args = list(args)
                args.insert(1, session)
                args = tuple(args)
            else:
                await asyncio.sleep(3)
                # args[1].timeout.total += 1.5
                session: ClientSession = args[1]

                if args[1].closed is True:
                    session = get_aiohttp_session(timeout=1,
                                                  headers={"Accept": "*/*"})
                    args = list(args)
                    args[1] = session
                    args = tuple(args)
            try:
                return await func(*args, **kwargs)
            except (asyncio.TimeoutError,
                    ConnectionRefusedError,
                    ClientConnectorError,
                    ClientOSError):
                await asyncio.sleep(timeout + random.randint(0, 3))
                return await wrapper(*args, **kwargs)

        return wrapper

    return decorator

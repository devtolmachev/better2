import asyncio
import threading
import traceback
from multiprocessing import Queue, Event
from threading import Thread
from types import FunctionType

q = Queue(maxsize=800000)
event_process = Event()


def make_thread(func: FunctionType):
    def wrapper(*args, **kwargs):
        thread = Thread(target=func, args=(*args,), kwargs=kwargs)
        thread.start()

    return wrapper


def async_io_action(func: FunctionType):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(func(*args, **kwargs))
            if func.__name__ == 'parse':
                event: Event = args[0]
                event.set()

        except Exception as exc:
            print(traceback.format_exc())

            th: str = args[1]
            thread_dead = threading.active_count() - 2

            msg = (f'Произошла ошибка. Поток {th}. Ошибка:\n'
                   f'{traceback.format_exc()}.\nУмерло '
                   f'{thread_dead} потоков\n*************\n')

            with open('exceptions.txt', 'a') as f:
                f.write(msg)
        finally:
            loop.run_forever()

    return wrapper

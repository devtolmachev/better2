import asyncio
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Process, current_process
from threading import Thread, current_thread

from src.core.decorators.io import event_process, async_io_action
from src.core.parser.fonbet import start_work
from src.core.utils.authorization import selenium_main


@async_io_action
async def threads_run():
    tasks = [Thread(target=start_work, args=(event_process, f"Thread {i}"))
             for i in range(20)]
    for thread in tasks:
        thread.start()
        event_process.wait()

    print('Все потоки запущены')
    event_process.set()


async def main():
    pr = Process(target=selenium_main, args=(event_process,))
    pr.start()

    event_process.wait()
    event_process.clear()

    Process(target=threads_run).start()

    while True:
        time.sleep(50)


if __name__ == '__main__':
    asyncio.run(main())

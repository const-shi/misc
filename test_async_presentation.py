###########################################################################################
# Тест -- презентация про асинхронность в Питоне
###########################################################################################

import asyncio
import time
from asyncio.locks import Semaphore
from concurrent.futures import ThreadPoolExecutor


###########################################################################################
# Loop - Task - Coroutine - CoroutineFunction
###########################################################################################
# async def это асинхронная(корутинная) функция
# вызванная корутинная функция это корутина
# чтобы асинхронный код начал работать нужна таска(Таска это объект в котором работает корутина)
# Таска работает в лупе(loop), в лупе могут работать несколько тасок асинхронно

# несколько фактов:
# - в рамках одной таски корутины работают последовательно(не асинхронно)
# - если мы авэйтим то это не создает новую таску а продолжается выполнение в рамках текущей
# - одновременно в одном потоке работает только один луп


def test_simple():

    async def do_simple():
        tasks.append(asyncio.current_task())  # запомним таску в которой работает do_simple
        return await inner_do_simple()  # авэйтим корутины

    async def inner_do_simple():
        tasks.append(asyncio.current_task())  # запомним таску в которой работает inner_do_simple
        return await asyncio.sleep(0.1)

    tasks = []  # список тасок которые создадуться для выполнения корутин
    assert asyncio.iscoroutinefunction(do_simple)  # собственно..
    coro = do_simple()
    assert asyncio.iscoroutine(coro)  # собственно..
    asyncio.run(coro)  # здесь создастся loop и создастся одна таска и запустится в этом loop'е
    assert tasks[0] == tasks[1]  # таски в которых выполнялись корутины - это одна и таже таска




###########################################################################################
# Пример асинхронности
###########################################################################################
# запускаем 2 таски, если одна из них ожидает асинхронной операции (в данном случае sleep)
# то выплнение переходит следующей таске
# чтобы запустить две асинхронные функции асинхронно надо вызвать asyncio.wait (или gather) - она создаст
# для каждой корутины свою таску и таски будут выполняться асинхронно

def test_wait():

    async def async1():
        order.append("start1")
        await asyncio.sleep(0.1)
        order.append("end1")
        tasks.append(asyncio.current_task())

    async def async2():
        await asyncio.sleep(0.01)  # для точного порядка запуска
        order.append("start2")
        await asyncio.sleep(0.1)
        order.append("end2")
        tasks.append(asyncio.current_task())

    tasks = []  # список тасок которые создадуться для выполнения корутин
    order = []
    asyncio.run(asyncio.wait([async1(), async2()]))
    assert order == ["start1", "start2", "end1", "end2"]
    assert tasks[0] != tasks[1]




###################################################################################################
# Создание тасок create_task
###################################################################################################
# таски выполняются асинхронно даже если одна создана в другой

def test_create_task():

    async def async_1():
        asyncio.create_task(async_2())  # добавит вторую таску и запустит в ней async_2
        await asyncio.sleep(0.01)  # передадим выполнение другой таске
        order.append("start1")
        await asyncio.sleep(0.1)
        order.append("end1")
        tasks.append(asyncio.current_task())

    async def async_2():
        order.append("start2")
        await asyncio.sleep(0.1)
        order.append("end2")
        tasks.append(asyncio.current_task())

    tasks = []  # список тасок которые создадуться для выполнения корутин
    order = []
    asyncio.run(async_1())  # создаст одну таску и запустит в ней async_1
    assert order == ["start2", "start1", "end2", "end1"]
    assert tasks[0] != tasks[1]



###################################################################################################
# синхронизация тасок  - ожидание одной таской другой таски
###################################################################################################
# create_task создает таску - работать она начинает но не сразу а когда дойдёт очередь

def test_wait_task():

    async def async_task1():
        task2 = asyncio.create_task(async_task2())  # добавит вторую таску и запустит в ней do_create_task2
        order.append("start1")
        await asyncio.sleep(0.1)
        order.append("waiting for task2")
        await task2  # ожидаем завершения таски
        order.append("end1")

    async def async_task2():
        order.append("start2")
        await asyncio.sleep(0.1)
        order.append("end2")

    order = []
    asyncio.run(async_task1())  # создаст одну таску и запустит в ней do_create_task1
    assert order == ["start1", "start2", "waiting for task2", "end2", "end1"]





###################################################################################################
# ограничение кол-ва тасок - семафоры
###################################################################################################

def test_semaphore():

    async def f_using_semaphore(x, start_sleep):
        await asyncio.sleep(start_sleep)  # чтобы упорядочить старт
        async with semaphore:
            order.append("start" + x)
            await asyncio.sleep(0.5)
            order.append("end" + x)

    async def semaphore_test():
        nonlocal semaphore
        semaphore = Semaphore(2)  # семафор создается в эвент лупе
        await asyncio.wait([f_using_semaphore("1", 0.1), f_using_semaphore("2", 0.2), f_using_semaphore("3", 0.3)])
        assert order == ["start1", "start2", "end1", "start3", "end2", "end3"]

    semaphore, order = None, []
    asyncio.run(semaphore_test())





###################################################################################################
# запуск синхронного кода асинхронно
###################################################################################################
# run_in_executor выполняет синхронный код в отдельном потоке(или процессе) и получается асинхронно

def test_sync():

    async def async_f():
        order.append("start1")
        await asyncio.sleep(0.1)
        order.append("end1")

    def sync_f():
        time.sleep(0.01)
        order.append("start2")
        time.sleep(0.1)
        order.append("end2")

    async def sync_and_async_test():
        loop = asyncio.get_running_loop()
        await asyncio.wait([async_f(), loop.run_in_executor(None, sync_f, )])
        assert order == ["start1", "start2", "end1", "end2"]

    order = []
    asyncio.run(sync_and_async_test())



###################################################################################################
# запуск асинхронного кода из синхронного который запущен из асинхронного )
# очень не рекомендуется так делать, но например в тестах можно
###################################################################################################

def test_async_in_sync():

    async def async_in_sync_in_async():
        await asyncio.sleep(0.1)
        return 4

    def sync_in_async():
        """ здесь не можем 1) ни авэйтить 2)ни запустить asyncio.run потому что евент_луп уже есть и выдаст ошибку"""
        pool = ThreadPoolExecutor()
        result = pool.submit(asyncio.run, async_in_sync_in_async()).result()
        assert result == 4

    async def _async():
        sync_in_async()

    asyncio.run(_async())

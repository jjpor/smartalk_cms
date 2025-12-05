import asyncio
from smartalk.logger import logger
from smartalk.scripts.create_booking_calendars import setup_calendars

results = asyncio.run(setup_calendars())
logger.info(results)
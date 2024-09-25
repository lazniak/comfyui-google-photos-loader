import asyncio
from tqdm import tqdm
from .logging_config import log_message

class AsyncProgressBar:
    def __init__(self, total, desc="", unit=""):
        self.pbar = tqdm(total=total, desc=desc, unit=unit)

    async def update(self, n=1):
        self.pbar.update(n)
        await asyncio.sleep(0)  # Allow other tasks to run

    def close(self):
        self.pbar.close()

class MultiProgressBar:
    def __init__(self, logger):
        self.progress_bars = {}
        self.logger = logger

    def add_bar(self, key, total, desc="", unit=""):
        self.progress_bars[key] = AsyncProgressBar(total, desc, unit)

    async def update(self, key, n=1):
        if key in self.progress_bars:
            await self.progress_bars[key].update(n)

    def remove_bar(self, key):
        if key in self.progress_bars:
            self.progress_bars[key].close()
            del self.progress_bars[key]

    async def finish(self):
        for bar in self.progress_bars.values():
            bar.close()
        self.progress_bars.clear()

    def log(self, message, level='info'):
        log_message(self.logger, message, level)
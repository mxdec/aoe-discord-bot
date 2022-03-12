# Standard Library
import logging
from typing import Dict, List

# Third Party
import desert
import requests
from discord.ext import commands, tasks

from config.dataclass import Ladder, PlayerRank


class LadderClient:

    headers = {"Referer": "https://www.aoe2.net/"}

    def __init__(self, url: str, page_size: int = 10000) -> None:
        self.url = url
        self.page_size = page_size
        # ladder by country, one list per contry code (ex: self.ladder['FR'])
        self.national: Dict[str, List[PlayerRank]] = {}

    def getWorldLadder(self, start: int, length: int) -> Ladder:
        params = {'start': start, "length": length}
        logging.info(f"GET - start: {start}, end: {start + length - 1}")
        resp = requests.get(
            url=self.url,
            params=params,
            headers=self.headers,
        )
        raw = resp.json()
        rank = desert.schema(Ladder).load(raw)
        return rank

    @staticmethod
    def groupByNation(
        national: Dict[str, List[PlayerRank]],
        players: List[PlayerRank],
    ) -> dict:
        for pl in players:
            if any([pl.steam_id, pl.country_code, pl.rank, pl.rating]) is None:
                continue
            if pl.country_code in national:
                national[pl.country_code].append(pl)
            else:
                national[pl.country_code] = [pl]
            logging.debug(f"{pl.rank}: {pl.country_code} - {pl.name}")
        return national

    def refreshRank(self) -> None:
        logging.info("starting ladder refresh task")
        national = {}
        start = 0
        length = self.page_size
        ladder = self.getWorldLadder(start, length)
        national = self.groupByNation(national, ladder.data)
        # total = ladder.recordsTotal
        total = 10001
        while start < total - length:
            start += length
            ladder = self.getWorldLadder(start, length)
            national = self.groupByNation(national, ladder.data)
        # save refreshed national ranks
        self.national = national
        logging.info("ladder refresh task over")


class LadderCog(commands.Cog):
    def __init__(self, bot: commands.Bot, ladder: LadderClient):
        self.bot = bot
        self.index = 0
        self.ladder = ladder
        self.printer.start()

    @commands.command()
    async def rank(self, ctx):
        logging.info("received !rank command")
        try:
            name = self.ladder.national['FR'][0].name
            rank = self.ladder.national['FR'][0].rank
            await ctx.send(f'first french is {name}, ranked {rank}')
        except Exception as e:
            logging.error(f"no data: {str(e)}")
            await ctx.send('no data')

    @tasks.loop(minutes=1)
    async def printer(self):
        self.ladder.refreshRank()


class DiscordBot(commands.Bot):

    async def on_ready(self):
        logging.info(f'{self.user.name} has connected to Discord.')

# Standard Library
import logging
from typing import List

# Third Party
import desert
import requests
from discord.ext.commands import Bot

from config.dataclass import Ladder, PlayerRank


class RankScraper:

    headers = {"Referer": "https://www.aoe2.net/"}

    def __init__(self, url: str) -> None:
        self.url = url

    def getRanks(self, start: int, length: int) -> Ladder:
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
    def filterByCountry(
        players: List[PlayerRank],
        code: str
    ) -> List[PlayerRank]:
        filtered = []
        for pl in players:
            if any([pl.steam_id, pl.country_code, pl.rank, pl.rating]) is None:
                continue
            if pl.country_code == code:
                filtered.append(pl)
                logging.debug(f"{pl.rank}: {pl.country_code} - {pl.name}")
        return filtered

    def refreshRank(self, code: str) -> List[PlayerRank]:
        start = 0
        length = 10000
        rank = self.getRanks(start, length)
        total = rank.recordsTotal
        filtered = self.filterByCountry(rank.data, code)
        while start < total - length:
            start += length
            res = self.getRanks(start, length)
            filtered.extend(self.filterByCountry(res.data, code))
            rank.data.extend(res.data)
        for i, pl in enumerate(filtered):
            logging.debug(f"{i}: {pl.rank} - {pl.name}")
        return filtered


class DiscordBot(Bot):

    def __init__(self, command_prefix: str):
        super().__init__(command_prefix)

        @self.command(name='test')
        async def command_test(ctx):
            print("Hello world !")
            await ctx.send("Hello world !")

        @self.command(name='rank')
        async def command_rank(ctx):
            print("The rank.")
            await ctx.send("The rank.")

    async def on_ready(self):
        print(f'{self.user} has connected to Discord.')

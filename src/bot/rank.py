# Standard Library
from dataclasses import dataclass
import logging
from typing import Dict, List, Optional, Tuple

# Third Party
import desert
import requests
from discord.ext import commands, tasks
from discord import Embed

from config.dataclass import Ladder, Player, PlayerRank


@dataclass
class NationsLadder:
    """Rank by country."""

    world: Ladder
    # ladder by country (ex: self.nations['FR'])
    nations: Dict[str, List[PlayerRank]]


class LadderClient:
    """Gather public data from the website."""

    headers = {"Referer": "https://www.aoe2.net/"}

    def __init__(
        self,
        url: str,
        members: List[Player],
        page_size: int = 10000,
    ) -> None:
        self.url = url
        self.members = members
        self.page_size = page_size
        self.team_national: NationsLadder = None
        self.duel_national: NationsLadder = None

    def getWorldLadder(self, url: str, start: int, length: int) -> Ladder:
        params = {'start': start, "length": length}
        logging.info(f"GET - start: {start}, end: {start + length - 1}")
        resp = requests.get(
            url=url,
            params=params,
            headers=self.headers,
        )
        raw = resp.json()
        rank = desert.schema(Ladder).load(raw)
        return rank

    def groupByNation(
        self,
        national: Dict[str, List[PlayerRank]],
        players: List[PlayerRank],
    ) -> Dict[str, List[PlayerRank]]:
        for pl in players:
            if any([pl.steam_id, pl.country_code, pl.rank, pl.rating]) is None:
                continue
            if pl.country_code in national:
                national[pl.country_code].append(pl)
            else:
                national[pl.country_code] = [pl]
            logging.debug(f"{pl.rank}: {pl.country_code} - {pl.name}")
        return national

    def refreshLadder(self, url: str) -> NationsLadder:
        logging.info(f"{url}: refreshing ladder")
        nations = {}
        start = 0
        length = self.page_size
        world = self.getWorldLadder(url, start, length)
        nations = self.groupByNation(nations, world.data)
        total = world.recordsTotal
        while start < total - length:
            start += length
            tmp = self.getWorldLadder(url, start, length)
            world.data.extend(tmp.data)
            nations = self.groupByNation(nations, tmp.data)
        logging.info(f"{url}: refreshing over")
        return NationsLadder(world, nations)

    def refreshData(self) -> None:
        self.team_national = self.refreshLadder(f"{self.url}/rm-team")
        self.duel_national = self.refreshLadder(f"{self.url}/rm-1v1")


class LadderCog(commands.Cog):
    def __init__(self, bot: commands.Bot, ladder: LadderClient):
        self.bot = bot
        self.index = 0
        self.ladder = ladder
        self.refresh.start()

    @staticmethod
    def formatRankLine(
        index: int,
        player: PlayerRank,
        icon: Optional[str] = None,
    ) -> str:
        name = player.name
        # crop the name if too long
        if len(name) > 13:
            name = f"{name[:10]}..."
        id = player.profile_id
        link = f"https://www.aoe2.net/#profile-{id}"
        elo = player.rating
        fill = 2
        if index > 10:
            fill = 4
        pos = f"{str(index + 1).rjust(fill)}"
        if icon is None:
            icon = "military_medal"
            if index == 0:
                icon = "first_place"
            elif index == 1:
                icon = "second_place"
            elif index == 2:
                icon = "third_place"
        return f"`{pos}.`  :{icon}:  `{elo}`  [{name}]({link})"

    @staticmethod
    def getMembersRank(
        members: List[Player],
        national: Dict[str, List[PlayerRank]],
    ) -> List[Tuple[int, PlayerRank]]:
        rank = []
        for n, p in enumerate(national['FR']):
            filtered = [m for m in members if m.profileId == p.profile_id]
            if len(filtered) > 0:
                rank.append((n + 1, p))
        return rank

    @commands.command()
    async def rank(
        self,
        ctx: commands.context.Context,
        country: str,
    ):
        logging.info(f"received command: !rank {country}")
        members_teamrank = self.getMembersRank(
            self.ladder.members,
            self.ladder.team_national.nations,
        )
        members_duelrank = self.getMembersRank(
            self.ladder.members,
            self.ladder.duel_national.nations,
        )
        code = country.upper()
        try:
            total_players_duel_nation = len(self.ladder.duel_national.nations[code])
            total_players_duel_world = self.ladder.duel_national.world.recordsTotal
            total_players_team_nation = len(self.ladder.team_national.nations[code])
            total_players_team_world = self.ladder.team_national.world.recordsTotal
            duel_leader = members_duelrank[0]
            team_leader = members_teamrank[0]
        except IndexError:
            duel_leader = (1, PlayerRank())
            team_leader = (1, PlayerRank())
        except Exception as e:
            logging.error(f"no data: {str(e)}")
            await ctx.send('no data')
            return

        emb = Embed(
            title=f":flag_{country.lower()}:  Leaderboard",
            color=5814783,
        )
        emb.set_thumbnail(
            url='https://upload.wikimedia.org/wikipedia/fr/5/55/AoE_Definitive_Edition.png'
        )
        emb.add_field(
            name='Duel players',
            value=(
                f":flag_{country.lower()}: {total_players_duel_nation}\n"
                f":earth_africa: {total_players_duel_world}"
            ),
            inline=True,
        )
        emb.add_field(
            name='\u200b',
            value='\u200b',
        )
        emb.add_field(
            name='Team players',
            value=(
                f":flag_{country.lower()}: {total_players_team_nation}\n"
                f":earth_africa: {total_players_team_world}"
            ),
            inline=True,
        )
        emb.add_field(
            name='Duel Leader',
            value=f":trophy: [{duel_leader[1].name}](https://www.aoe2.net/#{duel_leader[1].profile_id})",
            inline=True,
        )
        emb.add_field(
            name='\u200b',
            value='\u200b',
        )
        emb.add_field(
            name='Team Leader',
            value=f":trophy: [{team_leader[1].name}](https://www.aoe2.net/#{team_leader[1].profile_id})",
            inline=True,
        )
        duel_national_strings = []
        for n in range(10):
            s = self.formatRankLine(n, self.ladder.duel_national.nations[code][n])
            duel_national_strings.append(s)
        team_national_strings = []
        for n in range(10):
            s = self.formatRankLine(n, self.ladder.team_national.nations[code][n])
            team_national_strings.append(s)
        duel_members = []
        for n, mb in members_duelrank:
            s = self.formatRankLine(n, mb, "beginner")
            duel_members.append(s)
        team_members = []
        for n, mb in members_teamrank:
            s = self.formatRankLine(n, mb, "beginner")
            team_members.append(s)
        emb.add_field(
            name='Top 10 Duel',
            value='\n'.join(duel_national_strings),
            inline=True,
        )
        emb.add_field(
            name='\u200b',
            value='\u200b',
        )
        emb.add_field(
            name='Top 10 Team',
            value='\n'.join(team_national_strings),
            inline=True,
        )
        emb.add_field(
            name='Your positions',
            value='\n'.join(duel_members),
            inline=True,
        )
        emb.add_field(
            name='\u200b',
            value='\u200b',
        )
        emb.add_field(
            name='\u200b',
            value='\n'.join(team_members),
            inline=True,
        )
        await ctx.send(embed=emb)

    @tasks.loop(minutes=10)
    async def refresh(self):
        self.ladder.refreshData()


class DiscordBot(commands.Bot):

    async def on_ready(self):
        logging.info(f'{self.user.name} has connected to Discord.')

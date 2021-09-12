# Standard Library
import asyncio
import logging
import time
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import List, Optional

# Third Party
import desert
import requests
import yaml
from aoe import WSClient, Match, Player


@dataclass
class Config:
    """The config file."""

    aoe_ws: str
    discord_hook: str
    players: List[Player]


@dataclass
class Discord:
    """The Discord client."""

    url: str

    def post_message(self, data: dict) -> None:
        time.sleep(5)
        try:
            resp = requests.post(self.url, json=data)
            logging.info(f"status code: {resp.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"discord: error on request: {e}")


@dataclass
class Team:
    """Class representing a team."""

    players: List[Player]
    number: int


@dataclass
class CurrentMatch:
    """Class representing a match with players sorted by team."""

    match: Match
    teams: List[Team]

    def versus_str(self) -> str:
        """Return list of players as string."""
        s = ""
        for i, team in enumerate(self.teams):
            for ip, pl in enumerate(team.players):
                s += pl.name
                if ip < len(team.players) - 1:
                    s += ", "
            if i < len(self.teams) - 1:
                s += " vs "
        return s


class Notifier:
    """The notifier engine."""

    def __init__(
        self, cli: WSClient, dsc: Discord, pls: List[Player]
    ) -> None:
        """Inits Actions."""
        self.cli = cli
        self.discord = dsc
        self.players = pls

    async def run(self) -> None:
        prev = await self.get_lastmatches()
        if prev is None:
            logging.error("could't initialize matches")
            return

        logging.info("recent matches initialized")
        while True:
            time.sleep(50)
            new = await self.get_lastmatches()
            if new is None:
                logging.error("couldn't get last matches")
                continue
            await self.check_results(prev, new)
            prev = new
            logging.info("matches refreshed")

    async def check_results(
        self, prev: List[CurrentMatch], new: List[CurrentMatch]
    ) -> None:
        """Post results for new matches."""
        for n in new:
            found = [p for p in prev if p.match.id == n.match.id]
            if not found:
                logging.info(f"match: {n.versus_str()}: finished")
                msg = self.format_message(n)
                self.discord.post_message(msg)

    def format_message(self, match: CurrentMatch) -> dict:
        """Format Discord message."""
        title = ""
        desc = ""
        color = 7506394  # blue
        teams = match.teams
        header = "Match results."

        # prefix with result only when 2 teams are playing
        if len(teams) == 2:
            # is the clan successful ?
            win = False
            teammates: List[Player] = []
            for pl in match.match.players:
                for clan_player in self.players:
                    if pl.profileId == clan_player.profileId:
                        teammates.append(pl)
                        if pl.won is True:
                            win = True

            # ensure this is not an internal clan match for training
            if len(teammates) <= len(match.match.players) / 2:
                header = ""
                for n, m in enumerate(teammates):
                    header += f"{m.name.capitalize()}"
                    if n < len(teammates) - 2:
                        header += ", "
                    elif n < len(teammates) - 1:
                        header += " and "
                # format title and color according to the result
                if win is True:
                    logging.info("the clan is victorious")
                    header += (
                        f" {'are' if len(teammates) > 1 else 'is'} victorious."
                    )
                    color = 5089895  # green
                else:
                    logging.info("the clan has been defeated")
                    header += f" {'have' if len(teammates) > 1 else 'has'} been defeated."
                    color = 10961731  # red
            else:
                logging.info("this was an internal match")

        # build message body
        for it, team in enumerate(teams):
            title += f"{len(team.players)}"
            for ip, pl in enumerate(team.players):
                if pl.countryCode:
                    desc += f":flag_{pl.countryCode.lower()}: "
                else:
                    desc += ":globe_with_meridians: "
                name = pl.name
                if pl.rating:
                    name += f" ({pl.rating})"
                desc += (
                    f"[{name}](https://www.aoe2.net/#profile-{pl.profileId})"
                )
                if pl.won is True:
                    desc += " :crown:"
                if ip < len(team.players) - 1:
                    desc += ", "
            if it < len(teams) - 1:
                title += " vs "
                desc += "\n**Versus**\n"

        # add match info
        if match.match.location is not None:
            title += f" on {match.match.location}"
        desc += f"\n\nGame: **{'Ranked ' if match.match.ranked else ''}"
        desc += f"{match.match.gameType}**"
        if match.match.server is not None:
            desc += f"\nServer: **{match.match.server}**"

        # find replay link
        logging.info("Looking for a valid record link")
        link = ""
        for pl in match.match.players:
            try:
                resp = requests.get(pl.rec)
                if resp.status_code == 200:
                    logging.info("Found a valid record link")
                    link = pl.rec
                    break
            except requests.exceptions.RequestException as e:
                logging.error(
                    f"couldn't validate the replay URL {pl.rec}, {e}"
                )
        if link:
            desc += f"\nReplay: **[Download]({link})**"

        return {
            "content": header,
            "embeds": [{
                "title": title,
                "description": desc,
                "color": color
            }]
        }

    async def get_lastmatches(self) -> Optional[List[CurrentMatch]]:
        """Get last matches and removes ongoing matches from the list."""
        current = []

        matches = await self.cli.get_lastmatches(self.players)
        if matches is None:
            return None

        for match in matches:
            teams = self.set_teams(match.players)
            current.append(CurrentMatch(match=match, teams=teams))

        return self.filter_matches(current)

    def set_teams(self, players: List[Player]) -> List[Team]:
        teams: list[Team] = []

        for player in players:
            # skip empty slots
            if player.name is None:
                continue

            # find player's team
            found = False
            for team in teams:
                if player.team > -1 and team.number == player.team:
                    team.players.append(player)
                    found = True

            # create team otherwise
            if found is False:
                teams.append(Team(
                    number=player.team,
                    players=[player]
                ))

        return teams

    @staticmethod
    def match_finished(match: CurrentMatch) -> bool:
        # ensure we have score for all players
        for pl in match.match.players:
            if pl.won is None:
                logging.error(f"match: {match.versus_str()}: still ongoing")
                return False
        return True

    def filter_matches(self, matches: List[CurrentMatch]) -> List[CurrentMatch]:
        """Removes ongoing matches from list."""
        return [m for m in matches if self.match_finished(m) is True]


async def main(config_file: str) -> None:
    logging.info(f"loading config file {config_file}")
    try:
        with open(config_file, "r") as stream:
            data = yaml.safe_load(stream)
            config = desert.schema(Config).load(data)

            cli = WSClient(url=config.aoe_ws)
            dsc = Discord(url=config.discord_hook)
            notifier = Notifier(cli, dsc, config.players)

            # run the infinite loop
            logging.info("starting AoE Notifier...")
            await notifier.run()
            logging.info("exiting...")

    except Exception as exc:
        logging.error(exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # parse arguments
    parser = ArgumentParser()
    parser.add_argument("--config-file", type=str, help="Path to config file.")
    args = parser.parse_args()

    # start
    asyncio.run(main(args.config_file))

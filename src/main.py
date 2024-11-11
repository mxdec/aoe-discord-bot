# Standard Library
import logging
import time
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import List, Optional

# Third Party
import requests
import yaml
from aoe import WorldsEdgeApiClient, ConfigPlayer, Match, Member


@dataclass
class Config:
    """The config file."""

    worldsedge_url: str
    discord_hook: str
    players: List[ConfigPlayer]


@dataclass
class Team:
    """Class representing a team."""

    members: List[Member]
    number: int


@dataclass
class TeamMatch:
    """Class representing a match with players sorted by team."""

    match: Match
    teams: List[Team]

    def versus_str(self) -> str:
        """Return list of players as string."""
        s = ""
        for i, team in enumerate(self.teams):
            for ip, mb in enumerate(team.members):
                s += mb.profile.alias
                if ip < len(team.members) - 1:
                    s += ", "
            if i < len(self.teams) - 1:
                s += " vs "
        return s


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


class Engine:
    """The notifier engine."""

    def __init__(self, cli: WorldsEdgeApiClient, dsc: Discord, pls: List[ConfigPlayer]) -> None:
        """Inits Actions."""
        self.cli = cli
        self.discord = dsc
        self.players = pls

    def run(self) -> None:
        prev = self.get_lastmatches()
        if prev is None:
            logging.error("could't initialize matches")
            return

        logging.info("recent matches initialized")
        while True:
            time.sleep(50)
            new = self.get_lastmatches()
            if new is None:
                logging.error("could't refresh matches")
                continue

            self.check_results(prev, new)
            prev = new
            logging.info("matches refreshed")

    def check_results(self, prev: List[TeamMatch], new: List[TeamMatch]) -> None:
            """Post results for new matches."""
            for n in new:
                found = [p for p in prev if p.match.id == n.match.id]
                if not found:
                    logging.info(f"new finished match: {n.versus_str()}")
                    msg = self.format_message(n)
                    self.discord.post_message(msg)

    def format_message(self, match: TeamMatch) -> dict:
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
            teammates: List[Member] = []
            for mb in match.match.members:
                for clan_player in self.players:
                    if mb.profile.id == clan_player.profileId:
                        teammates.append(mb)
                        if pl.won is True:
                            win = True

            # ensure this is not an internal clan match for training
            if len(teammates) <= len(match.match.members) / 2:
                header = ""
                for n, m in enumerate(teammates):
                    header += f"{m.profile.alias.capitalize()}"
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
            title += f"{len(team.members)}"
            for ip, mb in enumerate(team.members):
                if mb.profile.country:
                    desc += f":flag_{mb.profile.country.lower()}: "
                else:
                    desc += ":globe_with_meridians: "
                name = mb.profile.alias
                name += f" ({mb.oldrating})"
                desc += f"[{name}](https://www.aoe2insights.com/user/{mb.profile.id}/)"
                if mb.outcome > 0:
                    desc += " :crown:"
                if ip < len(team.members) - 1:
                    desc += ", "
            if it < len(teams) - 1:
                title += " vs "
                desc += "\n**Versus**\n"

        # add match info
        title += f" on {match.match.mapname.split('.')[0].capitalize()}"

        ladder = self.ladder_description(match.match.matchtype_id)
        if ladder is not None:
            desc += f"\n\nGame: **{ladder}**"

        # find replay link
        logging.info("Looking for a valid record link")
        if match.match.replay:
            desc += f"\nReplay: **[Download]({match.match.replay})**"

        return {
            "content": header,
            "embeds": [{
                "title": title,
                "description": desc,
                "color": color
            }]
        }

    def ladder_description(self, matchtype_id: int) -> Optional[str]:
        """Formats the game type."""
        Gametypes = {
            0: 'Unranked',
            2: 'Ranked Deathmatch',
            6: 'Ranked Random Map 1v1',
            7: 'Ranked Random Map 2v2',
            8: 'Ranked Random Map 3v3',
            9: 'Ranked Random Map 4v4',
            26: 'Ranked Empire Wars 1v1',
            27: 'Ranked Empire Wars 2v2',
            28: 'Ranked Empire Wars 3v3',
            29: 'Ranked Empire Wars 4v4',
            120: 'Ranked Return of Rome 1v1',
            121: 'Ranked Return of Rome Team',
        }

        try:
            return Gametypes[matchtype_id]
        except KeyError:
            return None

    def get_lastmatches(self) -> Optional[List[TeamMatch]]:
            """Get last matches and removes ongoing matches from the list."""
            team_matches = []

            matches = self.cli.get_lastmatches(self.players)

            for match in matches:
                teams = self.set_teams(match.members)
                team_matches.append(TeamMatch(match=match, teams=teams))

            return team_matches

    def set_teams(self, members: List[Member]) -> List[Team]:
        teams: list[Team] = []

        for member in members:
            # find member's team
            found = False
            for team in teams:
                if member.teamid > -1 and team.number == member.teamid:
                    team.members.append(member)
                    found = True

            # create team otherwise
            if found is False:
                teams.append(Team(
                    number=member.teamid,
                    members=[member]
                ))

        return teams

def main(config_file: str) -> None:
    logging.info(f"loading config file {config_file}")

    try:
        with open(config_file, "r") as stream:
            data = yaml.safe_load(stream)
            config = Config(
                worldsedge_url=data["worldsedge_url"],
                discord_hook=data["discord_hook"],
                players=[
                    ConfigPlayer(
                        name=pl["name"],
                        steamId=pl["steamId"],
                        profileId=pl["profileId"],
                    )
                    for pl in data["players"]
                ],
            )

            cli = WorldsEdgeApiClient(url=config.worldsedge_url)
            dsc = Discord(url=config.discord_hook)
            engine = Engine(cli, dsc, config.players)

            # run the infinite loop
            logging.info("starting AoE Engine...")
            engine.run()
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
    main(args.config_file)

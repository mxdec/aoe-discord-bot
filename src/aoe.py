# Standard Library
import logging
from dataclasses import dataclass
from typing import List, Optional

# Third Party
import requests

@dataclass
class ConfigPlayer:
    """Represents the player in the config file."""

    name: Optional[str] = None
    profileId: Optional[int] = None
    steamId: Optional[str] = None


@dataclass
class Profile:
    """Represents the profile."""

    id: int
    name: str
    alias: str
    personal_statgroup_id: int
    xp: int
    country: str


@dataclass
class Member:
    """Represents the player in a match."""

    profile: Optional[Profile]
    civilization_id: int
    newrating: int
    oldrating: int
    outcome: int
    teamid: int


@dataclass
class Match:
    """Represents the match."""

    id: int
    mapname: str
    matchtype_id: int
    description: str
    startgametime: int
    completiontime: int
    replay: Optional[str]
    members: List[Member]


@dataclass
class PlayerMatches:
    """Private class that combines the player with his recent matches."""

    matches: List[Match]
    steam_id: str


class WorldsEdgeApiClient:
    """The HTTP client for World's Edge."""

    def __init__(self, url: str) -> None:
        self.url = url

    def get_matches(self, players: List[ConfigPlayer]) -> Optional[List[PlayerMatches]]:
        """Performs the HTTP requests."""
        pms: List[PlayerMatches] = []

        for pl in players:
            logging.info(f"getting {pl.name} (id: {pl.steamId}) matches...")

            resp = requests.get(f'{self.url}/community/leaderboard/getRecentMatchHistory?title=age2&profile_names=[%22/steam/{pl.steamId}%22]')
            if resp.status_code != 200:
                logging.error(f"HTTP request error with status: {resp.status_code}")
                return None

            data = resp.json()
            matches = data['matchHistoryStats']
            profiles = [
                Profile(
                    id=profile['profile_id'],
                    name=profile['name'],
                    alias=profile['alias'],
                    personal_statgroup_id=profile['personal_statgroup_id'],
                    xp=profile['xp'],
                    country=profile['country'],
                )
                for profile in data['profiles']
            ]

            parsedMatches = []
            for match in matches:
                matchMembers = [
                    Member(
                        profile=self.find_member_profile(profiles, member['profile_id']),
                        civilization_id=member['civilization_id'],
                        teamid=member['teamid'],
                        outcome=member['outcome'],
                        oldrating=member['oldrating'],
                        newrating=member['newrating']
                    )
                    for member in match['matchhistorymember']
                ]

                parsedMatch = Match(
                    id=match['id'],
                    mapname=match['id'],
                    matchtype_id=match['matchtype_id'],
                    description=match['description'],
                    startgametime=match['startgametime'],
                    completiontime=match['completiontime'],
                    members=matchMembers,
                    replay=self.get_replay(match['matchurls']),
                )
                parsedMatches.append(parsedMatch)

            pms.append(PlayerMatches(steam_id=pl.steamId, matches=parsedMatches))

        logging.info(f"found matches for {len(pms)}/{len(players)} players")
        return pms

    def get_lastmatches(self, players: List[ConfigPlayer]) -> Optional[List[Match]]:
        """Gathers last finished matchs for each player."""
        matches: List[Match] = []
        dedups: List[Match] = []

        pms = self.get_matches(players)
        if pms is None:
            return None

        # keep last 5 matches for each player
        for pm in pms:
            matches += pm.matches[:5]

        # remove duplicates
        for match in matches:
            if match.id in [d.id for d in dedups]:
                continue
            dedups.append(match)

        return dedups

    def find_member_profile(self, profiles: List[Profile], profile_id: int) -> Optional[Profile]:
        """Finds the profile by ID."""
        filtered_profiles = [profile for profile in profiles if profile.id == profile_id]

        if len(filtered_profiles) == 0: return None

        return filtered_profiles[0]

    def get_replay(self, match_urls: List[object]) -> None:
        """Extract the replay link."""
        if len(match_urls) == 0: return None

        return match_urls[0]['url']

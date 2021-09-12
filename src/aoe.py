# Standard Library
import json
import logging
from dataclasses import dataclass
from typing import List, Optional

# Third Party
import desert
import websockets


@dataclass
class Player:
    """Websocket object representing the Player."""

    avatar: Optional[str] = None
    avatarfull: Optional[str] = None
    avatarmedium: Optional[str] = None
    civ: Optional[int] = None
    civName: Optional[str] = None
    civAlpha: Optional[int] = None
    color: Optional[int] = None
    countryCode: Optional[str] = None
    name: Optional[str] = None
    profileId: Optional[int] = None
    rating: Optional[int] = None
    rec: Optional[str] = None
    slot: Optional[int] = None
    slotType: Optional[int] = None
    steamId: Optional[str] = None
    team: Optional[int] = None
    won: Optional[bool] = None


@dataclass
class Match:
    """Websocket object representing the match.

    If the match is not finished yet, the keys 'finished' and 'closed'
    are left empty. A unix timestamp is set otherwise.
    """

    active: bool
    appId: int
    averageRating: Optional[int]
    cheats: bool
    closed: Optional[int]
    finished: Optional[int]
    full: bool
    fullTechTree: bool
    gameType: str
    gameTypeId: int
    hasPassword: Optional[bool]
    hidden: bool
    id: str
    lastSeen: Optional[int]
    location: str
    lockSpeed: bool
    lockTeams: bool
    mapSize: str
    name: str
    numPlayers: int
    numSlots: int
    numSpectators: int
    players: List[Player]
    pop: int
    ranked: Optional[bool]
    ratingType: Optional[int]
    resources: str
    server: Optional[str]
    sharedExploration: bool
    speed: str
    started: int
    startingAge: str
    status: str
    steamLobbyId: Optional[str]
    turbo: bool
    victory: str
    visibility: str


@dataclass
class PlayerRecentMatches:
    """Websocket object representing the player's last matches."""

    data: List[Match]
    message: str
    id: str


@dataclass
class PlayerMatches:
    """Private class that combines the player with his recent matches."""

    matches: List[Match]
    player: Player


class WSClient:
    """The WS client for AoE2.net.

    The following messages are allowed:
    - {message: "playerprofile", id: <profile_id>})
    - {message: "playerhistorychart", id: <profile_id>})
    - {message: "playerleaderboardstats", id: <profile_id>})
    - {message: "playerrecentmatches", id: <profile_id>})
    - {message: "ping", data: <time_since_epoch_seconds>})

    Example:
        >>> ws = WSClient("wss://aoe2.net/ws")
        >>> players = Player(steamId="123456789", profileId="12345678")
        >>> matches = await ws.get_lastmatches(players, True)
        >>> print(matches)
    """

    headers = {
        "Origin": "https://www.aoe2.net",
    }

    def __init__(self, url: str) -> None:
        self.url = url

    async def get_matches(
        self, players: List[Player]
    ) -> Optional[List[PlayerMatches]]:
        pms: List[PlayerMatches] = []

        # connect to the server's socket
        try:
            ws = await websockets.connect(
                uri=self.url, ssl=True, extra_headers=self.headers
            )
        except Exception as e:
            logging.error(f"unable to connect to {self.url}: {e}")
            return

        logging.info("socket connected")
        # request the last matches for each player
        for pl in players:
            logging.info(f"getting {pl.name} (id: {pl.profileId}) matches...")
            try:
                await ws.send(
                    json.dumps(
                        {
                            "message": "playerrecentmatches",
                            "id": str(pl.profileId),
                        }
                    )
                )
            except Exception as e:
                logging.error(f"error while sending msg: {e}")
                break

            retry = 3
            while retry > 0:
                retry -= 1
                try:
                    raw = await ws.recv()
                    resp = json.loads(raw)
                    if (
                        "data" in resp
                        and isinstance(resp["data"], list)
                        and len(resp["data"]) > 0
                    ):
                        prm = desert.schema(PlayerRecentMatches).load(resp)
                        # remove empty slots from player list
                        for data in prm.data:
                            data.players = [
                                pl
                                for pl in data.players
                                if pl.name is not None
                            ]
                        pms.append(PlayerMatches(player=pl, matches=prm.data))
                        break
                    else:
                        logging.info(f"ignoring message: {raw}, {retry} left")
                except Exception as e:
                    logging.error(
                        f"error while getting {pl.name} matches: {e}"
                    )

        await ws.close()
        logging.info("socket closed")

        # log results
        msg = f"found matches for {len(pms)}/{len(players)} players"
        if len(pms) != len(players):
            logging.error(msg)
            return

        logging.info(msg)
        return pms

    async def get_lastmatches(
        self, players: List[Player]
    ) -> Optional[List[Match]]:
        """Gather last finished match for each player."""
        matches: List[Match] = []
        dedups: List[Match] = []

        # connect to the server's socket
        pms = await self.get_matches(players)
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

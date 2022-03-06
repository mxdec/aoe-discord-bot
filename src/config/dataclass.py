# Standard Library
from dataclasses import dataclass
from typing import List, Optional


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
class Config:
    """The config file."""

    players: List[Player]
    aoe_ws: Optional[str] = None
    discord_hook: Optional[str] = None
    discord_token: Optional[str] = None


# Json HTTP endpoint
@dataclass
class PlayerRank:
    """JSON HTTP object representing the player rank."""

    name: Optional[str] = None
    avatar: Optional[str] = None
    avatarfull: Optional[str] = None
    avatarmedium: Optional[str] = None
    steam_id: Optional[str] = None
    country_code: Optional[str] = None
    known_name: Optional[str] = None
    previous_rating: Optional[int] = None
    profile_id: Optional[int] = None
    rank: Optional[int] = None
    rating: Optional[int] = None
    highest_rating: Optional[int] = None
    num_games: Optional[int] = None
    streak: Optional[int] = None
    num_wins: Optional[int] = None
    win_percent: Optional[int] = None
    rating24h: Optional[int] = None
    games24h: Optional[int] = None
    wins24h: Optional[int] = None
    last_match: Optional[int] = None


@dataclass
class Ladder:
    """JSON HTTP object representing the ladder."""

    recordsFiltered: int
    data: List[PlayerRank]
    draw: int
    recordsTotal: int

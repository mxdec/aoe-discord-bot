# AoE Discord Bot

A Discord bot to notify the match results of your [Age of Empires](https://www.ageofempires.com/) community.

### Introduction

The goal of this project is to keep your community informed about your successes (and defeats) in Age of Empires 2 Definitive Edition by sending the results of your matches through Discord notifications.

Example:

<img src="./doc/screenshot.png" width="400">

> The bot collects game data from [AoE2.net](https://www.aoe2.net/).

### Requirements

Software:
- [python](https://www.python.org/downloads/release/python-370/) 3.7 or higher.

### Install on Ubuntu Focal

1. Update the package lists:
```
$ apt update
```

2. Install pip:
```
$ apt install -y python3-pip
```

3. Install the project dependencies:
```
$ pip3 install websockets desert pyyaml
```

4. Create the installation directory:
```
$ mkdir /etc/aoe
```

5. Put the sources inside:
```
$ ls -1 /etc/aoe/
aoe.py
main.py
```

### Usage

1. Edit the configuration file by filling your friends's Steam IDs and your Discord webhook:
```
$ cat /etc/aoe/config.yml
aoe_ws: "wss://aoe2.net/ws"
discord_hook: "https://discord.com/api/webhooks/your/token"
players:
- name: "TheViper"
  steamId: "76561197984749679"
  profileId: 196240
- name: "Hera"
  steamId: "76561198449406083"
  profileId: 199325
```

2. Start the service:
```
$ python3.8 /etc/aoe/main.py --config-file="/etc/aoe/config.yml"
```

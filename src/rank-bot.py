# Standard Library
from argparse import ArgumentParser
import yaml
import logging

# Third Party
import desert

from config.dataclass import Config
from bot.rank import DiscordBot, LadderCog, LadderClient


def main(config_file: str):
    logging.info(f"loading config file {config_file}")
    try:
        with open(config_file, "r") as stream:
            data = yaml.safe_load(stream)
            config = desert.schema(Config).load(data)

        bot = DiscordBot(command_prefix="!")
        ladder = LadderClient(config.aoe_ladder, config.players)
        cog = LadderCog(bot, ladder)
        bot.add_cog(cog)

        # run the infinite loop
        logging.info("starting AoE Rank Bot...")
        bot.run(config.discord_token)
        logging.info("exiting...")

    except Exception as exc:
        logging.error(exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # parse arguments
    parser = ArgumentParser()
    parser.add_argument("--config-file", type=str, help="Path to config file.")
    args = parser.parse_args()
    main(args.config_file)

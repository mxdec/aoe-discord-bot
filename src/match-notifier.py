# Standard Library
import asyncio
import logging
from argparse import ArgumentParser

# Third Party
import desert
import yaml
from notifier.scraper import WSClient, Discord, Notifier
from config.dataclass import Config


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

import os
from typing import Tuple, Optional, Dict
from dotenv import load_dotenv, find_dotenv
from configparser import ConfigParser
from scraper import Scraper
import json
from log import logger
import sys


def load_config() -> ConfigParser:
    """
    Load the configuration from the 'config.ini' file.

    Returns:
        ConfigParser: A ConfigParser object containing the configuration.
    """
    config = ConfigParser()
    config_file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_file_path)
    return config


def load_env_file(env_file: str) -> None:
    """
    Load environment variables from a specified .env file or a default location.

    Parameters:
        env_file (str): The path to the .env file or its filename (if located in the default location).
    """
    if '/' in env_file:
        dotenv_path = env_file
    else:
        dotenv_path = find_dotenv(env_file)
    load_dotenv(dotenv_path)


def load_env_variables() -> Tuple[str, str, Optional[str]]:
    """
    Load environment variables required for the Scraper.

    Returns:
        Tuple[str, str, Optional[str]]: A tuple containing the start URL, output file, and proxy (if provided).
    """
    start_url = os.getenv('INPUT_URL')
    output_file = os.getenv('OUTPUT_FILE')
    if config.getboolean('DEFAULT', 'use_proxy'):
        proxy = os.getenv('PROXY')
        logger.info(f'Proxy: {proxy}')
    else:
        proxy = None
        logger.info(f'Proxy usage disabled in config')

    if not start_url or not output_file:
        logger.error('NO INPUT URL OR OUTPUT FILE IN YOUR .env PLEASE CHECK IT OR USE ABSOLUTE PATH IN CONFIG')
        sys.exit()

    return start_url, output_file, proxy


def load_mapping_file(filename: str) -> Dict:
    """
    Load the mapping configuration from a JSON file.

    Parameters:
        filename (str): The filename of the JSON mapping file.

    Returns:
        Dict: A dictionary containing the mapping configuration.
    """
    try:
        with open(os.path.join(os.path.dirname(__file__), filename)) as file:
            mapping = json.load(file)
            logger.debug(f"Mapping.json: {mapping}")
    except FileNotFoundError as e:
        logger.error(str(e))
        raise FileNotFoundError("'mapping.json' file not found.")

    return mapping


if __name__ == '__main__':
    config = load_config()
    load_env_file(config.get('DEFAULT', 'env_filename'))
    start_url, output_file, proxy = load_env_variables()
    mapping = load_mapping_file('mapping.json')
    debug_mode = config.getboolean('DEFAULT', 'debug_mode')

    scraper = Scraper(
        debug_mode=debug_mode,
        start_url=start_url,
        proxy=proxy,
        output_file=output_file,
        mapping_file=mapping,
        wait_time=[config.getfloat('DEFAULT', 'min_wait_time'), config.getfloat('DEFAULT', 'max_wait_time')],
        random_user_agent=config.getboolean('DEFAULT', 'randomize_user_agent'),
    )

    scraped_data = scraper.main()

    with open(output_file, 'w') as file:
        json.dump(scraped_data, file)

    logger.info(f'Saved results in {output_file}')

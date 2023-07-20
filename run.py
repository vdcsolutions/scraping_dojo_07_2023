import os
from dotenv import load_dotenv, find_dotenv
from configparser import ConfigParser
from scraper import Scraper

config = ConfigParser()
config_file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
config.read(config_file_path)

env_file = config.get('DEFAULT', 'env_filename')

if '/' in env_file:
    dotenv_path = env_file
else:
    dotenv_path = find_dotenv(env_file)

load_dotenv(dotenv_path)

if __name__ == '__main__':
    Scraper(config).main()

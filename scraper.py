import os
from dotenv import load_dotenv, find_dotenv
from log import Logger
import json
from playwright.sync_api import sync_playwright, Page, Locator
import time
import random
from typing import List, Dict, Any, Union, Iterator
from configparser import ConfigParser
from fake_useragent import UserAgent
import sys
from parser import Parser


class Scraper:
    def __init__(self, config) -> None:
        """
        Initialize the Scraper object.

        This constructor loads environment variables, retrieves and logs them,
        loads the 'mapping.json' file as self.mapping, and reads configuration from 'config.ini'.

        Environment Variables:
            - PROXY (Optional[str]): Proxy information to be used for scraping.
            - INPUT_URL (Optional[str]): The input URL to be scraped.
            - OUTPUT_FILE (Optional[str]): The output file to save the scraped data.

        Mapping:
            The 'mapping.json' file is loaded as self.mapping, containing information
            about how to scrape the required data from the web pages.

        Configuration (from 'config.ini'):
            - min_wait_time (float): Minimum time to wait before clicking anything (randomly picked from the range).
            - max_wait_time (float): Maximum time to wait before clicking anything (randomly picked from the range).
            - use_proxy (bool): A boolean flag indicating whether to use a proxy for scraping.

        Raises:
            FileNotFoundError: If 'mapping.json' file is not found or 'config.ini' is not found.
        """
        self.debug_mode = config.getboolean('DEFAULT', 'debug_mode')
        self.logger = Logger('%(asctime)s - %(levelname)s - %(message)s', debug=self.debug_mode)
        # Retrieve environment variables
        self.proxy: Optional[str] = os.getenv('PROXY')
        self.input_url: [str] = os.getenv('INPUT_URL')
        self.output_file: [str] = os.getenv('OUTPUT_FILE')

        if not self.input_url:
            self.logger.error('NO INPUT URL OR OUTPUT FILE IN YOUR .env PLEASE CHECK IT OR USE ABSOLUTE PATH IN CONFIG')
            sys.exit()

        
        # Log environment variables
        self.logger.debug(f"Proxy: {self.proxy}")
        self.logger.debug(f"Input URL: {self.input_url}")
        self.logger.debug(f"Output File: {self.output_file}")

        # Load 'mapping.json' file as self.mapping
        mapping_file_path = os.path.join(os.path.dirname(__file__), 'mapping.json')
        try:
            with open(mapping_file_path) as file:
                self.mapping = json.load(file)
                self.logger.debug(f"Mapping.json: {self.mapping}")
        except FileNotFoundError as e:
            self.logger.error(str(e))
            raise FileNotFoundError("'mapping.json' file not found.")

        # Read configuration from 'config.ini'
        self.min_wait_time: float = config.getfloat('DEFAULT', 'min_wait_time')
        self.max_wait_time: float = config.getfloat('DEFAULT', 'max_wait_time')
        self.random_user_agent: bool = config.getboolean('DEFAULT', 'randomize_user_agent')
        self.restart_without_proxy: bool = config.getboolean('DEFAULT', 'restart_without_proxy')

        self.logger.info('Scraper initialized successfully')

    def delayed_click(self, element: Locator) -> None:
        """
        Perform a delayed click on the provided Playwright Locator.

        Args:
            element (Locator): The Playwright Locator representing the element to click.

        Raises:
            TimeoutError: If the element does not become visible within the specified time range.
        """
        if element.is_visible():
            wait_time = round(random.uniform(self.min_wait_time, self.max_wait_time), 2)
            self.logger.info(f"Waiting for {wait_time} seconds")
            time.sleep(wait_time)
            element.click()
        else:
            self.logger.error("Element not visible. Click action timed out.")
            raise TimeoutError("Element not visible. Click action timed out.")

    def scrape_data_from_page(self, page: Page) -> Dict[str, List[Any]]:
        """
        Scrape data from the given page using the provided mapping.

        Args:
            page (Page): The Playwright Page object representing the web page to scrape.

        Returns:
            Dict[str, List[Any]]: A dictionary containing the scraped data.
                                  The keys represent the data names, and the values are lists of scraped data.
        """
        scraped_data = {}

        for item in self.mapping['get']:
            name = item['name']
            xpath = item['xpath']
            element_type = item['type']

            page.wait_for_selector(xpath)

            elements = page.query_selector_all(xpath)
            if elements:
                values = [Parser.validate_element(element_type, element.inner_text()) for element in elements]
                scraped_data[name] = values

        return scraped_data

    def scrape_data_from_all_pages(self, page: Page) -> Iterator[Dict[str, List[Any]]]:
        """
        Scrape data from all pages using pagination.

        Args:
            page (Page): The Playwright Page object representing the initial web page to scrape.

        Yields:
            Iterator[Dict[str, List[Any]]]: An iterator yielding dictionaries containing the scraped data.
                                            Each dictionary represents data from a single page.
                                            The keys represent the data names, and the values are lists of scraped data.
                                            The iterator will stop when there are no more visible next pages to scrape.
        """
        scraped_data = self.scrape_data_from_page(page)
        yield scraped_data

        next_page_button = page.locator("xpath=" + self.mapping['paginate']['next_page_button_xpath'])
        while next_page_button.is_visible():
            self.delayed_click(next_page_button)
            scraped_data = self.scrape_data_from_page(page)
            yield scraped_data

            next_page_button = page.locator("xpath=" + self.mapping['paginate']['next_page_button_xpath'])

    def initialize_browser_instance(self, playwright, proxy):
        """
        Initialize the Playwright browser instance.

        If a proxy is provided, set it as a browser context option.
        If a random user agent is needed, set it as a browser context option.

        Returns:
            BrowserContext: The initialized Playwright BrowserContext instance.
        """
        if proxy:
            self.logger.info(f'Proxy: {proxy}')
            proxy = {'server': proxy}
        else:
            proxy = None
        browser = playwright.chromium.launch(proxy=proxy, headless=not self.debug_mode)

        if self.random_user_agent:
            user_agent = UserAgent().random
            browser.new_context(
                user_agent=user_agent
            )
            self.logger.info(f'User agent: {user_agent}')
        self.logger.info("Browser initialized succesfully")
        return browser, browser.new_page()

    def main(self) -> None:
        """
        Main method to initiate the scraping process.

        This method sets up the browser, navigates to the input URL,
        and performs the scraping using 'scrape_data_from_all_pages' method.
        The scraped data is then parsed using 'parse_scraped_data' and saved to the output file.

        Raises:
            Exception: If an error occurs during the scraping process.
        """
        with sync_playwright() as playwright:
            result: List[Dict[str, Any]] = []

            self.logger.info('Initializing browser')
            browser, page = self.initialize_browser_instance(playwright, self.proxy)

            try:
                page.goto(self.input_url)
            except Exception as e:
                self.logger.error(str(e))
                browser.close()
                if self.restart_without_proxy:
                    self.logger.info('Initializing browser again without proxy')
                    browser, page = self.initialize_browser_instance(playwright, None)
                    try:
                        page.goto(self.input_url)
                    except Exception as e:
                        self.logger.error(str(e))
                        raise
                else:
                    raise

            self.logger.info('Beginning scraping process')

            page_number = 0
            try:
                for scraped_data in self.scrape_data_from_all_pages(page):
                    page_number += 1
                    scraped_data = Parser.dict_with_lists_to_list_of_dicts(scraped_data)
                    result.extend(scraped_data)
                    self.logger.info(f"Page number {page_number} scraped successfully")
            except Exception as e:
                self.logger.error(str(e))
                page.screenshot(path='screenshot.png', full_page=True)
                raise

            browser.close()

        with open(self.output_file, 'w') as file:
            json.dump(result, file)

        self.logger.info(f'Result saved as {self.output_file}')


if __name__ == '__main__':
    config = ConfigParser()
    config_file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_file_path)

    env_file = config.get('DEFAULT', 'env_filename')

    if '/' in env_file:
        dotenv_path = env_file
    else:
        dotenv_path = find_dotenv(env_file)

    load_dotenv(dotenv_path)

    scraper = Scraper(config)
    scraper.main()

import os
from dotenv import load_dotenv, find_dotenv
from playwright.sync_api import sync_playwright, Page, Locator
import time
import random
from typing import List, Dict, Any, Union, Iterator
from configparser import ConfigParser
from fake_useragent import UserAgent
from parser import Parser
from log import logger

class Scraper:
    def __init__(
        self,
        debug_mode: bool,
        start_url: str,
        proxy: str,
        output_file: str,
        mapping_file: Dict,
        wait_time: List,
        random_user_agent: bool,
    ) -> None:
        """
        Initialize the Scraper object.

        Args:
            debug_mode (bool): Enable or disable debug mode for extra logging.
            start_url (str): The URL to start scraping from.
            proxy (str): The proxy server to be used for making HTTP requests.
            output_file (str): The file to store the scraped data.
            mapping_file (str): The file containing the mapping configuration.
            wait_time (list): Range of time to wait between consecutive requests.
            random_user_agent (bool): Use random user agents for each request.
            logger (logging.Logger): The logger object to handle logging.
        """

        self.mapping = mapping_file
        self.debug_mode = debug_mode
        self.start_url = start_url
        self.proxy = proxy
        self.output_file = output_file
        self.wait_time = wait_time
        self.random_user_agent = random_user_agent
        if debug_mode:
            logger.enable_debug_mode()

    def delayed_click(self, element: Locator) -> None:
        """
        Perform a delayed click on the provided Playwright Locator.

        Args:
            element (Locator): The Playwright Locator representing the element to click.

        Raises:
            TimeoutError: If the element does not become visible within the specified time range.
        """
        if element.is_visible():
            wait_time = round(random.uniform(self.wait_time[0], self.wait_time[1]), 2)
            logger.info(f"Waiting for {wait_time} seconds")
            time.sleep(wait_time)
            element.click()
        else:
            logger.error("Element not visible. Click action timed out.")
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

        for item in self.mapping['scrape']:
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

        next_page_button = page.locator("xpath=" + self.mapping['pagination']['next_page_button_xpath'])
        while next_page_button.is_visible():
            self.delayed_click(next_page_button)
            page.wait_for_load_state("networkidle")
            scraped_data = self.scrape_data_from_page(page)
            yield scraped_data

            next_page_button = page.locator("xpath=" + self.mapping['pagination']['next_page_button_xpath'])

    def initialize_browser_instance(self, playwright, proxy):
        """
        Initialize the Playwright browser instance.

        If a proxy is provided, set it as a browser context option.
        If a random user agent is needed, set it as a browser context option.

        Returns:
            BrowserContext: The initialized Playwright BrowserContext instance.
        """
        if proxy:
            logger.info(f'Proxy: {proxy}')
            proxy = {'server': proxy}
        else:
            proxy = None
        browser = playwright.chromium.launch(proxy=proxy, headless=not self.debug_mode)

        if self.random_user_agent:
            user_agent = UserAgent().random
            browser.new_context(
                user_agent=user_agent
            )
            logger.info(f'User agent: {user_agent}')
        logger.info("Browser initialized succesfully")
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

            logger.info('Initializing browser')
            browser, page = self.initialize_browser_instance(playwright, self.proxy)

            try:
                page.goto(self.start_url)
                page.wait_for_load_state("networkidle")
            except Exception as e:
                logger.error(str(e))
                browser.close()
                if self.restart_without_proxy:
                    logger.info('Initializing browser again without proxy')
                    browser, page = self.initialize_browser_instance(playwright, None)
                    try:
                        page.goto(self.start_url)
                        page.wait_for_load_state("networkidle")
                    except Exception as e:
                        logger.error(str(e))
                        raise
                else:
                    raise

            logger.info('Beginning scraping process')

            page_number = 0
            try:
                for scraped_data in self.scrape_data_from_all_pages(page):
                    page_number += 1
                    scraped_data = Parser.dict_with_lists_to_list_of_dicts(scraped_data)
                    result.extend(scraped_data)
                    logger.info(f"Page number {page_number} scraped successfully")
            except Exception as e:
                logger.error(str(e))
                page.screenshot(path='screenshot.png', full_page=True)
                raise

            browser.close()
            return result


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

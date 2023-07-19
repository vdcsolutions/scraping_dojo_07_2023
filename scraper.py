import os
from dotenv import load_dotenv
from log import Logger
import json
from playwright.sync_api import sync_playwright, Page, Locator
import time
import random
from typing import List, Dict, Any, Union, Iterator
from configparser import ConfigParser
from tqdm import tqdm

config = ConfigParser()
config_file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
config.read(config_file_path)
debug_mode = config.getboolean('DEFAULT', 'debug_mode')
logger = Logger('%(asctime)s - %(levelname)s - %(message)s', debug=debug_mode)


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
        # Load environment variables from the 'sigmoidal.env' file in the 'venv' directory
        dotenv_path = os.path.join(os.path.dirname(__file__), 'venv', 'sigmoidal.env')
        load_dotenv(dotenv_path)

        # Retrieve environment variables
        self.proxy: Optional[str] = os.getenv('PROXY')
        self.input_url: Optional[str] = os.getenv('INPUT_URL')
        self.output_file: Optional[str] = os.getenv('OUTPUT_FILE')

        # Log environment variables
        logger.debug(f"Proxy: {self.proxy}")
        logger.debug(f"Input URL: {self.input_url}")
        logger.debug(f"Output File: {self.output_file}")

        # Load 'mapping.json' file as self.mapping
        mapping_file_path = os.path.join(os.path.dirname(__file__), 'mapping.json')
        try:
            with open(mapping_file_path) as file:
                self.mapping = json.load(file)
                logger.debug(f"Mapping.json: {self.mapping}")
        except FileNotFoundError as e:
            logger.error(str(e))
            raise FileNotFoundError("'mapping.json' file not found.")

        # Read configuration from 'config.ini'
        try:
            self.min_wait_time: float = config.getfloat('DEFAULT', 'min_wait_time')
            self.max_wait_time: float = config.getfloat('DEFAULT', 'max_wait_time')
            self.random_user_agent: bool = config.getboolean('DEFAULT', 'randomize_user_agent')
        except FileNotFoundError as e:
            logger.error(str(e))
            raise FileNotFoundError("'config.ini' file not found.")
        logger.info('Scraper initialized successfully')

    def delayed_click(self, element: Locator) -> None:
        """
        Perform a delayed click on the provided Playwright Locator.

        Args:
            element (Locator): The Playwright Locator representing the element to click.

        Raises:
            TimeoutError: If the element does not become visible within the specified time range.
        """
        # Calculate the wait time for tqdm progress bar

        if element.is_visible():
            wait_time = round(random.uniform(self.min_wait_time, self.max_wait_time), 2)
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

        # Iterate over each item in the mapping and scrape the data
        for item in self.mapping['get']:
            name = item['name']
            xpath = item['xpath']
            element_type = item['type']

            # Wait for the element to appear on the page
            page.wait_for_selector(xpath)

            # Extract the elements based on the given XPath
            elements = page.query_selector_all(xpath)
            if elements:
                # Validate and process the elements based on their data types
                values = [self.validate_element(element_type, element.inner_text()) for element in elements]
                scraped_data[name] = values
        # Return the parsed and scraped data
        return scraped_data

    def validate_element(self, data_type: str, element: str) -> Union[str, List[str]]:
        """
        Validate and process the provided 'element' based on the specified 'data_type'.

        Args:
            data_type (str): The type of data processing to be applied. Accepted values:
                             - 'string': Convert the element to a string.
                             - 'list': Split the element into a list of words.
                             - 'list[n:m]': Slice the element into a list from index 'n' to 'm'.
            element (str): The element to be validated and processed.

        Returns:
            Union[str, List[str]]: The processed element based on the data_type.
                                   - If data_type is 'string', returns the element as a string.
                                   - If data_type is 'list', returns a list of words from the element.
                                   - If data_type is 'list[n:m]', returns a list sliced from index 'n' to 'm'.
                                   - If data_type is invalid, raises a ValueError.

        Raises:
            ValueError: If an invalid data_type is specified.
        """

        if '[' in data_type:
            temp = data_type.split('[')
            data_type = temp[0]
            slice_start = int(temp[1][0])
            try:
                slice_end = int(temp[1][-2])
            except:
                slice_end = int(-1)
        if data_type == "string":
            return str(element)
        elif data_type == "list":
            return str(element).split()[slice_start:slice_end]
        elif 'list' and '[' in data_type:
            return str(element.split('[')[0]).split()
        else:
            logger.error("Invalid data type specified")
            raise ValueError("Invalid data type specified")

    def parse_scraped_data(self, scraped_data: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        Parse the scraped data to generate a list of dictionaries.

        Args:
            scraped_data (Dict[str, List[Any]]): A dictionary containing the scraped data.
                                                The keys represent the data names,
                                                and the values are lists of scraped data.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary contains data from a single entry.
                                  The keys in the dictionary represent the data names,
                                  and the values represent the corresponding scraped data.

        Example:
            If 'scraped_data' is {'name': ['Alice', 'Bob'], 'age': [30, 25]},
            the function will return [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}].
        """
        result = []
        for key, values in scraped_data.items():
            for i, element in enumerate(values):
                if i < len(result):
                    result[i].update({key: element})
                else:
                    # If the result list is not large enough, create a new dictionary and append it
                    result.append({key: element})

        return result

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
        next_page_button = page.locator("xpath=" + self.mapping['paginate']['next_page_button_xpath'])
        n = 1

        # Scrape data from the initial page
        scraped_data = self.scrape_data_from_page(page)
        yield scraped_data

        # Iterate over subsequent pages using pagination
        while next_page_button.is_visible():
            n += 1
            self.delayed_click(next_page_button)
            # Scrape data from the current page
            scraped_data = self.scrape_data_from_page(page)
            yield scraped_data

            # Update the 'next_page_button' locator for the next iteration
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
            logger.info(f'Proxy: {proxy}')
            proxy = {'server': proxy}
        else:
            proxy = None
        browser = playwright.chromium.launch(proxy=proxy, headless=not debug_mode)
        # Set random user agent option if needed
        if self.random_user_agent:
            from fake_useragent import UserAgent
            random_ua = UserAgent().random
            browser.new_context(
                user_agent=random_ua
            )
            logger.info(f'User agent: {random_ua}')
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

            # Create an empty list to store the final result
            result: List[Dict[str, Any]] = []

            logger.info('Initializing browser')
            browser, page = self.initialize_browser_instance(playwright, self.proxy)

            try:
                page.goto(self.input_url)
            except Exception as e:
                logger.error(str(e))
                logger.info('Could not load page, restarting browser without proxy')
                browser.close()

                try:
                    browser, page = self.initialize_browser_instance(playwright, None)
                    page.goto(self.input_url)
                except Exception as e:
                    logger.error(str(e))
                    raise

            logger.info('Beginning scraping process')

            try:
                # Scrape data from all pages using pagination
                page_number = 0
                for scraped_data in self.scrape_data_from_all_pages(page):
                    page_number += 1
                    scraped_data = self.parse_scraped_data(scraped_data)
                    logger.debug(scraped_data)
                    result.extend(scraped_data)
                    logger.info(f"Page number {page_number} scraped successfully")
            except Exception as e:
                # If an error occurs during the scraping process, take a screenshot
                # and log the error message
                logger.error(str(e))
                page.screenshot(path='screenshot.png', full_page=True)
                raise
            logger.info('Scraping ended. Closing browser and saving results into file')
            # Close the browser
            browser.close()

            # Save the result to the output file as JSON
        with open(self.output_file, 'w') as file:
            json.dump(result, file)
            logger.info(f'Result saved as {self.output_file}')


if __name__ == '__main__':
    # Create an instance of the Scraper class
    scraper = Scraper(config)

    # Call the scrape method to start the scraping process
    scraper.main()

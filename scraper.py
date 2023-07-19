import os
from dotenv import load_dotenv
from logs import Logger
import json
from playwright.sync_api import sync_playwright
import time
import random

logger = Logger('%(asctime)s - %(levelname)s - %(message)s')
class Scraper:
    def __init__(self):

        # Load environment variables
        dotenv_path = os.path.join(os.path.dirname(__file__), 'venv', 'sigmoidal.env')
        load_dotenv(dotenv_path)

        # Retrieve environment variables
        self.proxy = os.getenv('PROXY')
        self.input_url = os.getenv('INPUT_URL')
        self.output_file = os.getenv('OUTPUT_FILE')

        # Log environment variables
        logger.debug(f"Proxy: {self.proxy}")
        logger.debug(f"Input URL: {self.input_url}")
        logger.debug(f"Output File: {self.output_file}")

        # Load mapping.json file as self.instructions
        with open('mapping.json') as file:
            self.mapping = json.load(file)
            logger.debug(self.mapping)


    def scrape_data_from_page(self, page):
        scraped_data = {}
        for item in self.mapping['get']:
            name = item['name']
            xpath = item['xpath']
            element_type = item['type']

            # Wait for the element to appear on the page
            page.wait_for_selector(xpath)

            # Extract the element based on its type
            elements = page.query_selector_all(xpath)
            if elements:
                values = [self.validate_scraped_element(element_type, element.inner_text()) for element in elements]
                scraped_data[name] = values
        return scraped_data

    def validate_scraped_element(self, data_type, element):
        if data_type == "string":
            return str(element)
        elif data_type == "list":
            return str(element).split()[1:]
        else:
            raise ValueError("Invalid data type specified")

    def scrape_data_from_all_pages(self, page):
        next_page_button = page.locator("xpath=" + self.mapping['paginate']['next_page_button_xpath'])
        n = 1
        scraped_data = self.scrape_data_from_page(page)
        logger.debug(f'{n} pages scraped!')
        yield scraped_data
        while next_page_button:
            n += 1
            time.sleep(random.uniform(2,5))
            next_page_button.click()
            scraped_data = self.scrape_data_from_page(page)
            logger.debug(f'{n} pages scraped!')
            yield scraped_data

    def main(self):
        with sync_playwright() as playwright:
            keys = [item['name'] for item in self.mapping['get']]
            result = {key: [] for key in keys}
            browser = playwright.chromium.launch(headless=False)
            page = browser.new_page()

            # Navigate to the input URL
            page.goto(self.input_url)
            #scraped_data = self.scrape_data_from_page(page)
            for scraped_data in self.scrape_data_from_all_pages(page):
                #logger.debug(scraped_data)
                for key in keys:
                    result[key].extend(scraped_data[key])

            with open(self.output_file, 'w') as file:
                json.dump(result, file)
                logger.debug(f'Result saved as {self.output_file}')



if __name__ == '__main__':
    # Create an instance of the Scraper class
    scraper = Scraper()

    # Call the scrape method to start the scraping process
    scraper.main()


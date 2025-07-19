import csv
import logging
import re   # regular expression implicitly used by converters
import random
import time
import traceback    # TODO:

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import yaml

# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('crawl_error.log', encoding='utf-8'),
        logging.StreamHandler()  # Also print to console
    ]
)


class Element:
    def __init__(self, field, selector, converter=None, timeout=1000):
        self.field = field
        self.selector = selector
        self.converter = converter
        self.timeout = timeout

    def extract(self, page):
        try:
            # page.wait_for_selector(self.selector, timeout=self.timeout)
            locator = page.locator(self.selector).first
            value = locator.text_content(timeout=self.timeout).strip()
            if self.converter:
                value = self.converter(value)
            return value
        except PlaywrightTimeoutError as e:
            print(f'Timeout while extracting {self.field}: {e}')
            logging.error(traceback.format_exc())
            return ''
        except Exception as e:
            print(f'Error extracting {self.field}: {e}')
            logging.error(traceback.format_exc())
            return ''


class Crawler:
    def __init__(self, crawl_key):
        config = Crawler.load_config(crawl_key)
        self.config = {
            'base_url': config.get('base_url'),
            'output_file': config.get('output_file', f'{crawl_key}.csv'),
            'retry': config.get('retry', 3),
            'scroll': config.get('scroll', False),
            'timeout': {
                'page': config.get('timeout', {}).get('page', 3000),
                'element': config.get('timeout', {}).get('element', 1000)
            }
        }

        # parameters. e.g. product code
        try:
            with open(config.get('param_file'), 'r', encoding='utf-8') as input_file:
                reader = csv.reader(input_file)
                self.params = [{f'param{i + 1}': v for i, v in enumerate(row)} for row in reader if any(row)]
        except Exception as e:
            print(f'Error: loading parameters from file: {e}')
            logging.error(traceback.format_exc())
            self.params = []

        # field name, selector, converter
        self.fields = [(field[0], field[1], eval(field[2]) if len(field) > 2 else None)
                       for field in config.get('fields', [])]

    @staticmethod
    def load_config(target):
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        if not config:
            print(f'No configuration found for site: {target}')
            return
        return config.get(target, {})

    def crawl(self):
        if not self.params:
            print('No parameters given.')
            return

        with open(self.config['output_file'], mode='w', newline='', encoding='utf-8-sig') as output_file:
            fieldnames = [name for name, _, _ in self.fields] + ['URL']
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()

            with sync_playwright() as pwright:
                print('Start crawling...')
                browser, context = Crawler.open_context(pwright)
                page = context.new_page()

                for product in self.extract(page):
                    print(product)
                    writer.writerow(product)
                    time.sleep(random.uniform(1.5, 3.5))    # human-like action: Delaying

                print('Closing browser...')
                browser.close()

    @staticmethod
    def open_context(pwright):
        print('Opening browser...')
        browser = pwright.chromium.launch(
            executable_path='chromium/chrome-win/chrome.exe',
            headless=True)
        context = browser.new_context(
            # spoof a real Chrome browser
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/138.0.7204.158 Safari/537.36'
            ),
            # randon window size
            viewport={'width': random.randint(1280, 1366), 'height': random.randint(720, 900)}
        )

        # spoof a real Chrome browser
        #   prevent detection of automated browsers
        #   avoid detection of missing language list
        #   simulate real browser plugins
        #   act like a real OS
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en-US'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        """)

        return browser, context

    def open_page(self, page, url):
        print(f'Opening: {url}')

        for attempt in range(self.config['retry']):
            try:
                page.goto(url, timeout=self.config['timeout']['page'], wait_until='domcontentloaded')
                break
            except PlaywrightTimeoutError:
                print(f'Retry {attempt + 1} for {url}')
                time.sleep(1)
        else:
            print(f'Cannot open {url}. Retry limit ({self.config["retry"]}) exceeded')
            logging.error(traceback.format_exc())
            return False

        # Crawler.scroll(page)   # human-like action: Scrolling
        return True

    @staticmethod
    def scroll(page):
        scroll_height = page.evaluate('() => document.body.scrollHeight')
        if scroll_height > 0:
            for _ in range(0, scroll_height, 500):
                page.mouse.wheel(0, 500)
                time.sleep(random.uniform(0.3, 0.7))

    def extract(self, page):
        for params in self.params:
            url = self.config['base_url'].format(**params)
            if not self.open_page(page, url):
                continue

            product = {}
            for field in self.fields:
                elem = Element(*field, timeout=self.config['timeout']['element'])
                product[elem.field] = elem.extract(page)
            product['URL'] = url
            yield product


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Crawl data using site-specific configuration.')
    parser.add_argument('crawl_key', help='Crawling target name in config.yaml.')
    args = parser.parse_args()

    Crawler(crawl_key=args.crawl_key).crawl()

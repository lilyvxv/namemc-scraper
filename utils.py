from pyvirtualdisplay import Display
from traceback import format_exc
from selenium import webdriver
from lxml import html
import threading
import datetime
import warnings
import time
import json
import sys
import re

warnings.filterwarnings("ignore", category=DeprecationWarning)

if sys.platform == 'linux':
    display = Display(visible=0, size=(800, 600))
    display.start()

class ScrapeData:
    def __init__(self) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-web-security')
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self.driver = webdriver.Chrome(options=options)
        #self.driver.set_window_size(0,0)
        #self.driver.set_window_position(0,0)
        self.driver.get('about:blank')

    def scrape(self, uri):
        script = ''.join([
            'function request(uri) {',
            '    var xmlHttp = new XMLHttpRequest();',
            '    xmlHttp.open( "GET", uri, false );',
            '    xmlHttp.send( null );',
            '    return xmlHttp.responseText',
            '}',
            'return request("{}")'.format(uri)
        ])

        response = self.driver.execute_script(script)
        return response


class ParseProfile:
    def __init__(self) -> None:
        self.REGEX = re.compile(r'.+\((\d+)\)')
        self.NAME_HISTORY_COUNT_XPATH = '/html/body/main/div[2]/div[1]/div[4]/div[2]/table/tbody/tr[1]/td[1]'
        self.FAVORITE_SERVER_COUNT_XPATH = '/html/body/main/div[2]/div[1]/div[6]/div[1]/strong'
        self.UUID_XPATH = '/html/body/main/div[2]/div[1]/div[1]/div[2]/div[1]/div[3]/samp'
        self.UUID_XPATH_2 = '/html/body/main/div[2]/div[1]/div[2]/div[2]/div[1]/div[3]/samp'
        self.NAME_XPATH = '/html/body/main/div[1]/div[1]/h1'
        self.FOLLOWING_COUNT_XPATH = '//*[@id="following-tab"]'
        self.FOLLOWERS_COUNT_XPATH = '//*[@id="followers-tab"]'
        self.CAPES_COUNT_XPATH = '/html/body/main/div[2]/div[2]/div[4]/div[1]/strong/text()'
        self.SEARCHES_XPATH = '/html/body/main/div[2]/div[1]/div[1]/div[2]/div[3]/div[2]'

    def parse(self, data):
        self.page_source = html.fromstring(data)
        try:
            self.setup()
            self.parse_name_history()
            self.parse_following_list()
            self.parse_followers_list()
            self.parse_favorite_servers()
            self.parse_rank()
            self.parse_socials()
            self.parse_capes()
            self.parse_skins()
        except:
            #print(format_exc())
            pass

        if self.name is None:
            return {'success': False, 'error': 'Profile does not exist'}, 404


        self.data = {
            'success': True,
            'name': self.name,
            'uuid': self.uuid,
            'searches': self.searches,
            'rank': self.rank,
            'socials': self.socials,
            'hidden_names': self.hidden_names,
            'name_history': self.name_history,
            'following': {'count': self.following_count, 'names': self.following_list},
            'followers': {'count': self.followers_count, 'names': self.followers_list},
            'favorite_servers': {'count': self.favorite_server_count, 'names': self.favorite_servers},
            'skins': {'count': self.skins_count, 'links': self.skins},
            'capes': {'count': self.capes_count, 'optifine': self.optifine, 'names': self.capes},
        }

        return self.data, 200

    def setup(self):
        self.searches = self.page_source.xpath(self.SEARCHES_XPATH)
        if self.searches != []:
            self.searches = int(self.searches[0].text.split(' / ')[0])
        else:
            self.searches = 0

        self.following_count = self.page_source.xpath(self.FOLLOWING_COUNT_XPATH)
        if self.following_count != []:
            self.following_count = int(self.REGEX.match(self.following_count[0].text).group(1))
        else:
            self.following_count = 0
                    
        self.followers_count = self.page_source.xpath(self.FOLLOWERS_COUNT_XPATH)
        if self.followers_count != []:
            self.followers_count = int(self.REGEX.match(self.followers_count[0].text).group(1))
        else:
            self.followers_count = 0

        self.favorite_server_count = self.page_source.xpath(self.FAVORITE_SERVER_COUNT_XPATH)
        if self.favorite_server_count != []:
            self.favorite_server_count = int(self.favorite_server_count[0].text.split('(')[1].split(')')[0])
        else:
            self.favorite_server_count = 0

        self.capes_count = self.page_source.xpath(self.CAPES_COUNT_XPATH)
        if self.capes_count != []:
            if self.capes_count[0] != ' Cape':
                self.capes_count = int(self.capes_count[0].split('(')[1].split(')')[0])
            else:
                self.capes_count = 0
        else:
            self.capes_count = 0

        try: self.name_history_length = int(self.page_source.xpath(self.NAME_HISTORY_COUNT_XPATH)[0].text)
        except: self.name_history_length = 0
        try:
            self.uuid = self.page_source.xpath(self.UUID_XPATH)[0].text
        except IndexError:
            self.uuid = self.page_source.xpath(self.UUID_XPATH_2)[0].text
        except:
            self.uuid = None
        try: self.name = self.page_source.xpath(self.NAME_XPATH)[0].text
        except: self.name = None

    def convert_to_unix(self, time):
        return int(datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())
        
    def parse_name_history(self):
        self.name_history = []
        self.hidden_names = 0
        for i in range(1, self.name_history_length * 2, 2):
            try:
                username = self.page_source.xpath(f'/html/body/main/div[2]/div[1]/div[4]/div[2]/table/tbody/tr[{i}]/td[2]/a')[0].text
            except:
                username = self.page_source.xpath(f'/html/body/main/div[2]/div[1]/div[4]/div[2]/table/tbody/tr[{i + 2}]/td[2]/span')
                username = None
                self.hidden_names += 1

            try:
                time = self.page_source.xpath(f'/html/body/main/div[2]/div[1]/div[4]/div[2]/table/tbody/tr[{i}]/td[3]/time')[0].attrib['datetime']
                time = self.convert_to_unix(time)
                timef_number = self.page_source.xpath(f'/html/body/main/div[2]/div[1]/div[4]/div[2]/table/tbody/tr[{i + 1}]/td[3]')[0].text
                timef_letter = self.page_source.xpath(f'/html/body/main/div[2]/div[1]/div[4]/div[2]/table/tbody/tr[{i + 1}]/td[3]/small')[0].text
                timef = timef_number + timef_letter
            except:
                time = None
                timef = None

            self.name_history.append({'username': username, 'datetime': time, 'time_formatted': timef})

    def parse_following_list(self):
        self.following_list = []
        for i in range(1, self.following_count + 1):
            try:
                username = self.page_source.xpath(f'//*[@id="following"]/a[{i}]')[0].text
                if username != '…':
                    self.following_list.append(username)
            except:
                return

    def parse_followers_list(self):
        self.followers_list = []
        for i in range(2, self.followers_count + 2):
            try:
                username = self.page_source.xpath(f'//*[@id="followers"]/a[{i}]')[0].text
                if username != '…':
                    self.followers_list.append(username)
            except:
                return

    def parse_favorite_servers(self):
        self.favorite_servers = []
        for i in range(1, self.favorite_server_count + 1):
            try:
                server = self.page_source.xpath(f'/html/body/main/div[2]/div[1]/div[6]/div[2]/a[{i}]/text()')[0]
                if server != '…':
                    self.favorite_servers.append(server)
            except:
                pass

    def parse_rank(self):
        try:
            self.rank = self.page_source.xpath('/html/body/main/div[2]/div[1]/div[1]/div[2]/div[4]/div[2]/a')[0].text
            if '\n' in self.rank:
                self.rank = 'Default'
        except:
            self.rank = 'Default'
    
    def parse_socials(self):
        self.socials = []
        elements = self.page_source.xpath('//a[@class="d-inline-block position-relative p-1"]')
        for element in elements:
            try:
                data = element.attrib['data-content']
            except:
                data = element.attrib['href']
            try:
                name = element.attrib['data-original-title']
            except:
                name = element.attrib['title']
            self.socials.append({'name': name, 'data': data})

    def parse_capes(self):
        self.capes = []
        self.optifine = False

        for i in range(1, self.capes_count + 1):
            name = self.page_source.xpath(f'/html/body/main/div[2]/div[2]/div[4]/div[2]/div/a[{i}]')[0].attrib['title']
            #link = 'https://namemc.com' + self.page_source.xpath(f'/html/body/main/div[2]/div[2]/div[4]/div[2]/div/a[{i}]')[0].attrib['href']
            self.capes.append({'name': name})
        try:
            self.page_source.xpath('/html/body/main/div[2]/div[2]/div[4]/div[1]/strong/a')[0]
            self.optifine = True
        except:
            pass
        try:
            self.page_source.xpath('/html/body/main/div[2]/div[2]/div[5]/div[1]/strong/a')[0]
            self.optifine = True
        except:
            pass

    def parse_skins(self):
        self.skins = []
        
        try:
            self.skins_count = int(self.page_source.xpath('/html/body/main/div[2]/div[2]/div[3]/div[1]/strong/a')[0].text)
        except:
            pass

        for i in range(100):
            try:
                url = self.page_source.xpath(f'/html/body/main/div[2]/div[2]/div[3]/div[2]/div/a[{i}]/canvas')[0].attrib['data-id']
                url = f'https://s.namemc.com/i/{url}.png'
                self.skins.append(url)
            except:
                pass


class ScrapeThree:
    def __init__(self):
        self.START_URL = 'https://namemc.com/minecraft-names?sort=asc&length_op=eq&length=3&lang=&searches=0'
        self.NAMES = []
        self.TEMP_NAMES = []
    
    def setup(self, scraper):
        self.scraper = scraper
        threading.Thread(target = self.scraper_loop).start()
        
    def scraper_loop(self):
        while True:
            try:
                self.TEMP_NAMES = []
                response = self.scraper.scrape('https://namemc.com/minecraft-names?sort=asc&length_op=eq&length=3&lang=&searches=0')
                page_source = html.fromstring(response)
                self.next_url = 'https://namemc.com' + page_source.xpath('/html/body/main/div/div[2]/nav/ul/li[4]/a')[0].attrib['href']
                names = self.parse_names(page_source)
                droptimes = self.parse_droptimes(page_source)
                for name in names:
                    droptime = droptimes[names.index(name)]
                    self.TEMP_NAMES.append({'name': name, 'droptime': droptime})
                if not len(names) < 60:
                    self.get_next_pages()

                self.NAMES = self.TEMP_NAMES
            except:
                pass

            time.sleep(120)
    
    def get_next_pages(self):
        while True:
            try:
                response = self.scraper.scrape(self.next_url)
                page_source = html.fromstring(response)
                self.next_url = 'https://namemc.com' + page_source.xpath('/html/body/main/div/div[2]/nav/ul/li[4]/a')[0].attrib['href']
                names = self.parse_names(page_source)
                droptimes = self.parse_droptimes(page_source)
                for name in names:
                    droptime = droptimes[names.index(name)]
                    self.TEMP_NAMES.append({'name': name, 'droptime': droptime})
                if len(names) < 60:
                    return
            except:
                pass

    def parse_names(self, page_source):
        try:
            names = []
            for i in range(1, 500, 1):
                name = page_source.xpath(f'/html/body/main/div/div[4]/div/table/tbody/tr[{i}]/td[1]/a/text()')
                if name != []:
                    names.append(name[0])
            return names
        except:
            pass

    def parse_droptimes(self, page_source):
        try:
            droptimes = []
            for i in range(1, 500, 1):
                droptime = page_source.xpath(f'/html/body/main/div/div[4]/div/table/tbody/tr[{i}]/td[1]/time')
                if droptime != []:
                    droptime = droptime[0].attrib['datetime']
                    droptime = self.convert_to_unix(droptime)
                    droptimes.append(droptime)
            return droptimes
        except:
            pass

    def convert_to_unix(self, time):
        return int(datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())
    
    def get_names(self):
        return self.NAMES


class CacheHandler:
    def __init__(self) -> None:
        self.timeout = 120
        pass


    def find(self, name, scraper, parser):
        with open('cache.json', 'r') as f:
            file_data = json.load(f)
            f.close()

        if name in file_data:
            user_data = file_data[name]
            if user_data['last_updated'] + self.timeout < time.time():
                print('Cache outdated... rescraping!')

                response = scraper.scrape(f'https://namemc.com/{name}')
                data, status_code = parser.parse(response)

                user_data['last_updated'] = time.time()
                user_data['data'] = data
                user_data['status_code'] = status_code

                with open('cache.json', 'w') as write:
                    json.dump(file_data, write)
                    f.close()

                return data, status_code

            else:
                print(f'Name will expire in {user_data["last_updated"] + self.timeout - time.time()} seconds.')
                return user_data['data'], user_data['status_code']
        
        else:
            print('Name not in cache... scraping!')

            response = scraper.scrape(f'https://namemc.com/{name}')
            data, status_code = parser.parse(response)

            file_data[name] = {
                'last_updated': time.time(),
                'data': data,
                'status_code': status_code
            }

            with open('cache.json', 'w') as write:
                json.dump(file_data, write)
                f.close()

            return data, status_code

# encoding:utf-8
import sys
import time
from tqdm import tqdm
import logging
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from pyvirtualdisplay import Display
from pymongo.errors import DuplicateKeyError

from fb_parse.statsd import StatsClient
from fb_parse.database.MongoConnector import MongoConnect
from fb_parse.configs.config import MONGO_ADDR, MONGO_DB, brubeck_host, brubeck_post
from fb_parse.decorators import run_in_new_thread

logger = logging.getLogger(__name__)

class FB_parser():

    def __init__(self, fb_group, mongo_collection='fb_adverts'):
        self.mongo_collection = MongoConnect(MONGO_ADDR, MONGO_DB, mongo_collection)
        self.statsd = StatsClient(brubeck_host, brubeck_post)
        self.fb_group = fb_group
        self.driver = None
        self.dups_count = 0
        self.post_class = '_q7o'
        self.author_name_class = 'fwb'
        self.author_string_class = 'fcg'
        self.price_class = '_l57'
        self.outer_link_class = '_6ks'
        self.location_class = '_l58'
        self.time_class = '_5ptz'
        self.seller_button_class = '_4jy0'
        self.more_button_class = 'text_exposed_link'
        self.post_text_class = 'userContent'
        self.photo_class = '_5dec'
        while not self.driver:
            try:
                self.display = Display(visible=0, size=(1024, 768))
                self.display.start()
                profile = webdriver.FirefoxProfile()
                profile.set_preference('intl.accept_languages', 'en')
                self.driver = webdriver.Firefox(firefox_profile=profile)
            except:
                logger.debug('can not start driver retring')
                logger.debug(sys.exc_info())
                time.sleep(1)

    def __del__(self):
        self.driver.close()

    def get_post_author(self, post):
        """
        :param post:
        :return: str
        """
        author_name = post.find_element_by_class_name(self.author_name_class).text
        return author_name

    def get_post_price(self, post):
        """
        :param post:
        :return: str
        """
        try:
            price = post.find_element_by_class_name(self.price_class).text
        except NoSuchElementException:
            price = None
        return price

    def get_post_was_link(self, post):
        """
        :param post:
        :return: str
        """
        try:
            authors_string = post.find_element_by_class_name(self.author_string_class).text
            was_link = 'shared a link' in authors_string or 'ссылкой' in authors_string
            outer_link = post.find_element_by_class_name(self.outer_link_class) \
                .find_element_by_tag_name('a') \
                .get_property('href')
        except NoSuchElementException:
            was_link = False
            outer_link = None
        return was_link, outer_link

    def get_post_location(self, post):
        """
        :param post:
        :return: str
        """
        try:
            location = post.find_element_by_class_name(self.location_class).text
        except NoSuchElementException:
            location = None
        return location

    def get_post_time(self, post):
        """
        UNIX time
        :param post:
        :return: int
        """

        time_area = post.find_element_by_class_name(self.time_class).get_attribute('data-utime')
        return int(time_area)

    def get_post_link(self, post):
        """
        :param post:
        :return: str
        """
        try:
            link = post.find_element_by_class_name('_5pcq').get_property('href')
        except NoSuchElementException:
            link = post.find_element_by_class_name('fsm').find_element_by_tag_name('a').get_property('href')
        return link

    def get_post_write_to_seller(self, post):
        """
        :param post:
        :return: str
        """
        try:
            write_to_seller = post.find_element_by_class_name(self.seller_button_class).text
        except:
            write_to_seller = False
        return write_to_seller

    def get_post_text(self, post):
        """
        :param post:
        :return: str
        """
        text_area = ''
        # If there're "more" click it
        try:
            post.find_element_by_class_name(self.more_button_class).click()
        except NoSuchElementException:
            pass

        user_content_elements = post.find_elements_by_class_name(self.post_text_class)
        for user_content in user_content_elements:
            if user_content:
                text_area += user_content.text
                text_area += '\n'
        return text_area

    def get_post_photos(self, post):
        """
        :param post:
        :return: list
        """
        photo_elements = post.find_elements_by_class_name(self.photo_class)
        photos_url_list = list()
        for elem in photo_elements:
            elem_url = elem.get_attribute('data-ploi')
            photos_url_list.append(elem_url)
        return photos_url_list

    def get_posts(self):
        """
        :param post:
        :return: list
        """
        try:
            posts = self.driver.find_elements(By.CLASS_NAME, self.post_class)
            return posts
        except NoSuchElementException:
            # TODO шлём метрику в statsd
            logger.error(f'no posts found under {self.post_class}')
            raise NoSuchElementException


    def save_to_db(self, advert):
        try:
            self.mongo_collection.collection.insert_one(advert)
        except DuplicateKeyError:
            self.dups_count += 1
            logger.debug(f'duplicated {advert["_id"]}')

    @run_in_new_thread
    def process_group(self, scroll_times=10):
        self.driver.base_url = self.fb_group
        self.driver.get(self.fb_group)
        post_processed = 0
        for _ in tqdm(range(scroll_times), desc=self.fb_group):
            posts = self.get_posts()
            for post in posts[post_processed:]:
                result_dict = dict()
                result_dict['time'] = self.get_post_time(post)
                result_dict['text'] = self.get_post_text(post)
                result_dict['photos'] = self.get_post_photos(post)
                result_dict['author'] = self.get_post_author(post)
                result_dict['link'] = self.get_post_link(post)
                result_dict['write_to_seller'] = self.get_post_write_to_seller(post)
                result_dict['was_link'], result_dict['outer_link'] = self.get_post_was_link(post)
                result_dict['group'] = self.fb_group
                result_dict['location'] = self.get_post_location(post)
                result_dict['price'] = self.get_post_price(post)
                result_dict['_id'] = result_dict['link'].split('/')[-2]
                self.save_to_db(result_dict)
                post_processed += 1
                # TODO шлём метрику в statsd

            if self.dups_count > 20:
                break
            else:
                self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
                time.sleep(5)


if __name__ == '__main__':
    fb_parser = FB_parser('https://www.facebook.com/groups/735597296550141/', mongo_collection='test_adverts')
    fb_parser.process_group()
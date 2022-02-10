# by no_skills_ben
# Big thnks to Aaron Rudkin who's R scraper had the direct donation url link that makes this script possible
    # https://github.com/aaronrudkin/give_send_go

# this script reads the comments from the freedom convoy givesendgo comapaign or any givesendgo campaign for frther analysis

# even though the data is returned in json like text, it gets captcha'd by cloudflare if we just use requests so...
# got to get that physical browser up with selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# json to convert the returned donations
import json

# got to check if ye olde file exists
from os import path

# pandas are cute
import pandas as pd

# because the time info on the donation is relative we need the current time as of the read.
import datetime

# sleepytime
import time
import random

# import demoji to convert emotes to descriptive text
import demoji

class HonkHonk:
    """
        This class reads all the comments from a givesendgo campaign.
        Originally created to read the canadian "freedom" convoy of 2022.
        This does not save campaign info other than the campaign id, just all the donations.

        Requirements:
            in python
            - Selenium
            - pandas
            -demoji (for emote reading)
            other
            - The Crhome web driver for selenium. https://chromedriver.chromium.org/downloads
                - NOTE: if you just download it, it wont be in your "PATH" so you will need to speciy the path in
                         the webdriver_path_if_needed variable.

        Usage: find the campaign id by inspecting a givesendgo's campaign page and searching for "campaign_id"
        then instance HokHonk with
        csv_file_name: str = a valid csv file name or full path with file name (include .csv)
        campaign_id: int = the campaign id you found.
        OPTIONAL:
        webdriver_path_if_needed: str = the absolute path the the chrome driver.

        then use .read() to read the donations to the file
        if read_until_existing_id = true then it reads new donations until it hits one already saved in the csv file. so
        you dont need to read allll the donations every time you want to get new ones.
    """
    # df = pandas dataframe becaus for some reason pandas is always pd and dataframes are always df?
    df = None

    # no notes on these
    file_name = None
    campaign_id = None
    webdriver_path_if_needed = ''

    # used to read backwards in recent donations
    min_donation_id = None
    read_donations_id = []

    hit_existing_id = False

    def __init__(self, csv_file_name: str, campaign_id: int, webdriver_path_if_needed: str = ''):
        """
        Set's a instance up to read all the donations of 1 givesendgo campaing to a specified csv file

        :param csv_file_name: relative or absolute path to a csv file that exists or you want to create. (include .csv)
        :param campaign_id: campaing_id found by inspecting the campaign page code and searching "campaign_id"
        :param webdriver_path_if_needed: if chrome web driver is not in your path variable put the absolute path to it here
        """

        # stores the campaign id
        self.campaign_id = campaign_id

        #stores the filename
        self.file_name = csv_file_name

        # loads the dataframe from the csv file in he working directory or creates the empty dataframe
        if path.exists(csv_file_name):
            self.df = pd.read_csv(csv_file_name)

        #     loads the read donation id's and the min id so you can resume a big read
            self.read_donations_id = self.df['donation_id'].tolist()
            self.min_donation_id = min(self.read_donations_id)
        else:
            self.df = pd.DataFrame(columns=[
                'donation_id',
                'campaign_id',
                'donation_amount',
                'donation_comment',
                'donation_conversion_rate',
                'donation_name',
                'donation_anonymous',
                'donation_date',
                'lovecount',
                'likes',
                'relative_date'])

        #  stores the path for the webdriver to use
        if webdriver_path_if_needed:
            self.webdriver_path_if_needed = webdriver_path_if_needed

    def _load_page(self,driver: webdriver,url: str):
        """
        Internal function to load a page. seperated from read to make it easier to read the code.

        :param driver: instanced driver
        :param url: the url to load
        :return: a dict from the page json or an empty dict
        """

        # returns an empty list if the driver is not open
        if not driver.session_id:
            return {}
        else:

            # TODO: replace nare try statement.. try harder
            # waits for the pre element to load.
            try:
                driver.get(url)
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//pre"))
                )
            except:
                return {}
            # reads the json text and returns it as a list
            jsontext = element.text
            return json.loads(jsontext)

    def _dump_data(self,page_data: dict):
        """
        reads the page's dict data, adds it to the data frame and returns a bool to indicate the script should keep reading

        :param page_data: a loaded page's json object converted to a list of dicts
        :return: a bool to state if the script should keep reading donations
        """
        # set keep reading as true
        keep_reading = True

        # try to load donations up and get the page code
        try:
            donations = page_data['returnData']['donations']
        except KeyError:
            donations = []

        try:
            page_code = page_data['code']
        except KeyError:
            page_code = None

        # if there's no donations it's time to end the script but lets see if it failed.
        if not donations:
            keep_reading = False
            if page_code == 200:
                print('no more donations')
            else:
                print(f'page did not load properly, code if any={page_code}')
                print(f'page data if any = {page_data}')
        else:
            # get the current datetime
            now_text = str(datetime.datetime.now())

            # going item by item instead of more efficient methods just to catch duplicates
            cur_donations = []
            for donation in donations:
                cur_donations.append(donation['donation_id'])
                donation['relative_date'] = now_text

                # convert emojii to descriptions
                donation['donation_comment'] = demoji.replace_with_desc(donation['donation_comment'])

                if not donation['donation_id'] in self.read_donations_id:
                    temp_df = pd.DataFrame([donation])
                    self.df = pd.concat([self.df,temp_df], ignore_index=True, sort=False)
                    self.read_donations_id.append(donation['donation_id'])
                else:
                    self.hit_existing_id = True

            # get the lowest current min id to be able to load the next page
            self.min_donation_id = min(cur_donations)


        return keep_reading





    def read(self, read_until_existing_id: bool,start_from_min_id: bool):
        """

        :param read_until_existing_id: if this is set to true, it will stop reading when it hits an id that is already
                                        saved in the csv file. Used for getting new donos since your last read
        :param start_from_min_id: this resumes the read from the oldest existing id from the csv file. only useful for
                                    resuming crashed script or large campaigns
        :return: CSV fil with donation info
        """
        # just a little bool to see if we can keep going
        keep_alive = True

        # selenium web driver booted in it's pantaloons
        if self.webdriver_path_if_needed:
            # TODO: executable_path is depreciated fix this at some point
            driver = webdriver.Chrome(executable_path=self.webdriver_path_if_needed)
        else:
            driver = webdriver.Chrome()

        # if you dont want to get the missing old donation gap, set the min id back to nothing
        if not start_from_min_id:
            self.min_donation_id = None

        # now we either start or resume
        if not self.min_donation_id:
            # Ok, so we can only get 10 donations at a time. donation=null will get you the most recent and then using the
            # lowest donation id will get you the 10 next oldest donations after that id.
            url = f'https://givesendgo.com/donation/recentdonations?camp={self.campaign_id}&donation=null'

            # load the page
            page_data = self._load_page(driver=driver,url=url)
            # quit on no data
            if not page_data:
                print('could not load the first page')
                keep_alive = False
            else:
                if not self._dump_data(page_data=page_data):
                    print("first page loaded with no donations")
                    keep_alive = False
        tester= 0
        # endless loop... until it ends
        while keep_alive:
            # little crash protection
            tester +=1
            if tester >100:
                self.df.to_csv(self.file_name)
                tester=0
            # got my ip temp banned so now i'm making the loop take some naps.
            time.sleep(random.Random().randint(a=1, b=3))

            # to prevent it running once if the null page fails
            if keep_alive:
                # to close it down if last page hit an existing ID
                if read_until_existing_id and self.hit_existing_id:
                    keep_alive = False
                else:
                    # build the url with current min id
                    url = f'https://givesendgo.com/donation/recentdonations?camp={self.campaign_id}&donation={self.min_donation_id}'
                    # load the page
                    page_data = self._load_page(driver=driver, url=url)
                    # quit on no data
                    if not page_data:
                        print(f'could not load the page with donation_id={self.min_donation_id}')
                        keep_alive = False
                    else:
                        if not self._dump_data(page_data=page_data):
                            print(f"Page_loaded with no donations, donation {self.min_donation_id} might be the first donation")
                            keep_alive = False

        # check to see if any items were read at all
        if len(self.df.index) > 0:
            # overwrite ye olde csv file

            self.df.to_csv(self.file_name)



if __name__ == '__main__':
    # example usage
    freedom = HonkHonk(
        csv_file_name="truck_donors.csv",
        campaign_id=49000,
        webdriver_path_if_needed="E:\\BEN DOCS\\Downloads\\chromedriver_win32\\chromedriver.exe")
    freedom.read(read_until_existing_id=False, start_from_min_id=False)
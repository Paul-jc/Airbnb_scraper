#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  airbnb_iterate.py
#  
#  Copyright 2019 Paul Clarke <paul@Paul-jc>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  


from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
from selenium import webdriver
from tabulate import tabulate
from random import uniform
import pandas as pd
import numpy as np
import pyprind
import time
import bs4
import csv
import os

# TODO instantiate a chrome options object so you can set the size and headless preference
#proxy = "213.184.136.232:3128"


# Takes search parameters, gets all urls, gets listing details and writes to file
def run_program(check_in_date, check_out_date, suburb, state, output_file_name, report_file_name):
    cols = ['listing id string', 'listing id', 'listing price', 'listing type', 'no guests', 'bedroom type', 'no beds', 'bathroom type']
    url_list = get_url_list(check_in_date, check_out_date, suburb, state) # gets initial list of urls to search by price increments
    url_list = get_url_offsets(url_list) # retrieves number of pages for each search - appends these to the list
    print(str(len(url_list)) + ' urls in search') # returns number of urls that are in the list to console
    bar_total = len(url_list)
    progressBar = pyprind.ProgBar(bar_total, monitor = True , title = 'Retrieving listing data') # creates progress bar to track progess of program
    write_text_file = open('airbnb_url_list.txt', 'w')
    with open(output_file_name, 'w') as f:
        write_csv_file = csv.writer(f, dialect = 'excel')
        write_csv_file.writerow(cols) # creates labels for the top row the file
        for url in url_list:
            write_text_file.write(url + '\n')
            soup = get_page_html(url)
            get_listing_details(soup,write_csv_file)
            progressBar.update() # increments progress bar to the next step
    write_text_file.close()
    print(progressBar)# completes progress bar and prints total time take, CPU and memory usage
    write_report(output_file_name, report_file_name)


# Airbnb only returns 17 pages of data for each search so this function creates a list
# of urls to search at $50 increments in order to get all listings returned for the given search
def get_url_list(check_in_date, check_out_date, suburb, state):
    url_list = []
    check_in_date = check_in_date.strftime('%Y-%m-%d')
    check_out_date = check_out_date.strftime('%Y-%m-%d')
    for i in range(10, 990, 50): # starts with a search starting at $10, incrementing at $50 increments until it reaches a starting rate of $990 - any maximum price value over $1000 is treated as infinity
        min_price = str(i)
        max_price = str(i + 50) # makes max price $50 higher than minimum price in search
        url = ('https://www.airbnb.com.au/s/homes?refinement_paths%%5B%%5D=%%2Fhomes&checkin=%s&checkout=%s&adults=0&children=0&infants=0&toddlers=0&query=%s%%2C%%20%s&price_max=%s&price_min=%s&display_currency=AUD'
            % (check_in_date, check_out_date, suburb, state, max_price, min_price))
        url_list.append(url)
    return(url_list)


# Checks each search parameters and finds out how many pages are returned for that search and appends these page urls to the current list
def get_url_offsets(url_list):
    full_url_list = set()
    bar_total = len(url_list)
    progressBar = pyprind.ProgBar(bar_total, monitor = True , title = 'Retrieving URL list') # starts a progress bar to help keep track of program progress
    for url in url_list:
        soup = get_page_html(url)
        page_numbers = []
        # saves all page numbers that appear on the page
        for i in soup.findAll('div', {'class': '_1bdke5s'}): #page number elements on search landing page
            page_numbers.append(int(i.text))
        if len(page_numbers) == 0: # checks how many page number appear on the page and adds these urls to the list - if there are none it is assume there is only one page
            progressBar.update() # updates progress bar to next step
            full_url_list.add(url)
            continue
        else:
            pages = max(page_numbers)
            # adds all pages to url list
            for page_number in range(1, pages):
                if page_number == 1:
                    full_url_list.add(url)
                else:
                    offset = (page_number-1) * 18
                    full_url_list.add(url+'&items_offset='+str(offset))
            if pages == 17:
                # if there are 17 pages in the search it writes a record of this in case user wishes to check these searches in more detail
                writefile = open('airbnb_17_pages.txt', 'a')
                writefile.write(url)
                writefile.close()
        progressBar.update() # updates progress bar to next step
    print(progressBar) # completes progress bar and prints total time take, CPU and memory usage
    return full_url_list


# Scans retrieves html code and returns full code for processing
def get_page_html(url):
    # TODO insert function to retrieve and set proxy address
    chrome_options = Options()
    chrome_options.add_argument('--headless') # runs browswer window in the background so as to not interupt user experience
    chrome_options.add_argument('--window-size=1920x1080')
    #chrome_options.add_argument('--proxy-server=%s' % proxy)
    chrome_driver = "/usr/lib/chromium-browser/chromedriver"
    driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver)
    driver.get(url) #navigate to the page
    time.sleep(uniform(0.5,1.9)) # delay a random time between 0.5 to 1.9 seconds after each search to avoid overloading the website
    html = driver.page_source
    soup = bs4.BeautifulSoup(html, 'html.parser') # saves html to beautiful soup for further processing
    driver.close() # close browser before moving on
    return soup


# Takes the html for the page, iterates through each listing and retrieves each desired detail
def get_listing_details(soup, write_csv_file):
    for listing in soup.findAll('div', {'class': '_gig1e7'}): #frame around each listing
        listing_details = [] # new list created for each listing
        listing_details.append(get_listing_id(listing))
        listing_details.append(get_listing_id_string(listing))
        listing_details.append(get_listing_price(listing))
        listing_details.append(get_listing_type(listing))
        for i in get_listing_bedroom_type(listing).split(' · '): # in for loop because 3 pieces of data are in the same string
            listing_details.append(i)
        write_csv_file.writerow(listing_details) # list as a new row to output csv - wrote this one row at a time to avoid creating large DataFrame which may slow down processing on some computers


# Returns unique id for listing
def get_listing_id(listing):
    listing_id = listing.find('a')['target'] # unique identifyer for each listing on Airbnb
    return listing_id


# Converts listing id to numbers only for processing in this form
def get_listing_id_string(listing):
    listing_id = listing.find('a')['target'] # unique identifyer for each listing on Airbnb
    listing_id_string = listing_id.strip('listing_')
    return listing_id_string


# Retrieve price for listing
def get_listing_price(listing):
    try:
        price_string = listing.find('span', {'class': '_tw4pe52'}).text # total price for search
        price_integer = int(''.join(list(filter(str.isdigit, str(price_string)))))
        return(price_integer)
    except AttributeError:
        print('get_listing_price error')
        pass


# Retrieve string at top of listing that descibes if it is an entire premises or shared room ect
def get_listing_type(listing):
    try:
        for listing_type in listing.findAll('span', {'class': '_1xxanas2'}): # string at top of listing descibing listing
            # these strings are also tagged with the same identifier to the desired string so we want to skip these to get the desired data
            if not str(listing_type.string) == "None" and not listing_type.string == "Plus" and not listing_type.string == "RARE FIND":
                return(listing_type.string)
    except AttributeError:
        print('get_listing_type error')
        pass


# Retrieves number of bedrooms or studio ect, number of guests and bathrooms
def get_listing_bedroom_type(listing):
    try:
        bedroom_type = listing.find('div', {'class': '_1jlnvra2'}).text #string containing guest numbers, bedroom and bathroom details
        if bedroom_type is not None:
            return bedroom_type
        else:
            pass
    except AttributeError:
        print('get_listing_bedroom_type error')
        pass


def write_report(output_file_name, report_file_name):
    # Reads output file as a DataFrame for processing
    df = pd.read_csv(output_file_name)
    # Creates pivot table
    display_table = pd.pivot_table(df, index = ['listing type', 'bedroom type'],
                                values = ['listing price'],
                                # size is python's term for count so this will return the number of listings per type, and the minimum, mean and maximum rate of these listings
                                aggfunc=[np.size, np.min, np.mean, np.max],fill_value=0, margins = True)
    # Rounds pivot table to 2 decimal places
    display_table = np.round(display_table,2)
    # When printing a data that comes close to filling the page width pandas skips some data, this script prevents this from happening
    print(display_table)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        print(display_table)
    # Writes table to a new file for user to read in future
    display_table.to_csv(report_file_name)


# Asks user for parameters for search parameters through console

state = input('Enter state for search: ')

suburb = input('Enter suburb for search: ')
suburb = suburb.replace(' ', '%20')

check_in_date = str(input('Enter check-in date for scrape (yyyy-mm-dd): '))
check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d')

check_out_date = str(input('Enter check-out date for scrape (yyyy-mm-dd): '))
check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d')


"""
# Can be uncommented to automatically place parameters in search for faster testing
state = 'Victoria'
suburb = 'Sale'
check_in_date = '2019-04-03'
check_out_date = '2019-04-04'
file_name_check_in_date = str(datetime.strptime(check_in_date, '%Y-%m-%d'))
file_name_check_out_date = str(datetime.strptime(check_out_date, '%Y-%m-%d'))
file_name_check_in_date = file_name_check_in_date.strip(' 00:00:00')
file_name_check_out_date = file_name_check_out_date.strip(' 00:00:00')
check_in_date = datetime.strptime(check_in_date, '%Y-%m-%d')
check_out_date = datetime.strptime(check_out_date, '%Y-%m-%d')
"""
now = datetime.now()
cwd = os.getcwd() # retrieves directory that the python script is saved in
# Creates file name for output file
output_file_name = ('%s/airbnb_output_%s_%s_c-in-%s_c-out-%s_generated_%s.xlsx' 
                    % (cwd, state, suburb,check_in_date, check_out_date, now.strftime('%Y_%m_%d_%H:%M:%s')))
# Creates file name for report file
report_file_name = ('%s/airbnb_report_%s_%s_c-in-%s_c-out-%s_generated_%s.xlsx' 
                    % (cwd, state, suburb,check_in_date, check_out_date, now.strftime('%Y_%m_%d_%H:%M:%s')))


# Takes search perameters 
run_program(check_in_date, check_out_date, suburb, state, output_file_name, report_file_name)

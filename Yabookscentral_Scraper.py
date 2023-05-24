from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
import undetected_chromedriver as uc
import pandas as pd
import time
import csv
import sys
import numpy as np
import re 

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options  = webdriver.ChromeOptions()
    # suppressing output messages from the driver
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    # adding user agents
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # running the driver with no browser window
    chrome_options.add_argument('--headless')
    # disabling images rendering 
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'eager'
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_page_load_timeout(60)
    driver.maximize_window()

    return driver

def scrape_yabookscentral(path):

    start = time.time()
    print('-'*75)
    print('Scraping yabookscentral.com ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'yabookscentral_data.xlsx'
        # getting the books under each category
        links = []
        nbooks, npages = 0, 0
        while True:
            npages += 1
            url = f"https://www.yabookscentral.com/search-the-yabc-database/search-results/?pg={npages}&order=updated&query=all"
            driver.get(url)
            # scraping books urls
            titles = wait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[class='fwd-font-bold fwd-no-underline fwd-text-lg fwd-text-gray-900']")))
            for title in titles:
                try:
                    nbooks += 1
                    print(f'Scraping the url for book {nbooks}')
                    link = title.get_attribute('href')
                    links.append(link)
                except Exception as err:
                    print('The below error occurred during the scraping from yabookscentral.com, retrying ..')
                    print('-'*50)
                    print(err)
                    continue

            # checking the next page
            try:
                button = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[class='jr-pagenav-next jrButton jrSmall']")))
            except:
                break
                    
        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('yabookscentral_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('yabookscentral_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Scraping Books Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):
        try:
            if link in scraped: continue
            driver.get(link)           
            details = {}
            print(f'Scraping the info for book {i+1}\{n}')

            # title and title link
            title_link, title = '', ''              
            try:
                title_link = link
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').replace('\n', '').strip().title() 
            except:
                print(f'Warning: failed to scrape the title for book: {link}')               
                
            details['Title'] = title
            details['Title Link'] = title_link                          
            # Author and author link
            author, author_link = '', ''
            try:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrAuthor.jrFieldRow")))
                except:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrAuthorname.jrFieldRow")))
                tags = wait(div, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
                for tag in tags:
                    author += tag.get_attribute('textContent').replace('\n', '').strip().title() + ', '
                    author_link += tag.get_attribute('href') + ', '
            except:
                pass
                    
            details['Author'] = author[:-2]            
            details['Author Link'] = author_link[:-2]             
            # publisher
            publisher = ''
            try:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrPublisher.jrFieldRow")))
                except:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrPublishername.jrFieldRow")))
                publisher = wait(div, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrFieldValue"))).get_attribute('textContent').strip()
            except:
                pass          
                
            details['Publisher'] = publisher            
            
            # genre
            genre = ''
            try:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrGenre.jrFieldRow")))
                except:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrGenretype.jrFieldRow")))
                lis = wait(div, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "li")))
                for li in lis:
                    genre += li.get_attribute('textContent').strip() + ', '
            except:
                pass          
                
            details['Genre'] = genre[:-2]             
            
            # age
            age = ''
            try:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrAge.jrFieldRow")))
                except:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrAgegroup.jrFieldRow")))
                age = wait(div, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrFieldValue"))).get_attribute('textContent').strip()
            except:
                pass          
                
            details['Age'] = age            
            
            # ISBN
            ISBN = ''
            try:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrIsbnagain.jrFieldRow")))
                except:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrIsbnnumber.jrFieldRow")))
                ISBN = wait(div, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrFieldValue"))).get_attribute('textContent').strip()
            except:
                pass          
                
            details['ISBN'] = ISBN               
            
            # date
            date = ''
            try:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrDate.jrFieldRow")))
                except:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrPublisheddate.jrFieldRow")))
                date = wait(div, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrFieldValue"))).get_attribute('textContent').strip()
            except:
                pass          
                
            details['Publication Date'] = date             
            
            # Amazon Link
            Amazon = ''
            try:
                try:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrAmazon.jrFieldRow")))
                except:
                    div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrAsinnumber.jrFieldRow")))
                Amazon = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
            except:
                pass          
                
            details['Amazon Link'] = Amazon             
            
            # user ratings and count
            user_rating, user_count = '', ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrOverallUser.jrRatingsLarge")))
                text = wait(div, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.jrRatingValue.fwd-ml-2.fwd-text-sm"))).get_attribute('textContent')
                nums = re.findall("[0-9\.]+", text)
                if len(nums) == 2:
                    user_rating = nums[0]
                    user_count = nums[1]
                elif len(nums) == 1:
                    user_rating = nums[0]
            except:
                pass          
                
            details['User Rating'] = user_rating    
            details['User Ratings Count'] = user_count 

            # editor ratings and count
            editor_rating, editor_count = '', ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.jrOverallEditor.jrRatingsLarge")))
                text = wait(div, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.jrRatingValue.fwd-ml-2.fwd-text-sm"))).get_attribute('textContent')
                nums = re.findall("[0-9\.]+", text)
                if len(nums) == 2:
                    editor_rating = nums[0]
                    editor_count = nums[1]
                elif len(nums) == 1:
                    editor_rating = nums[0]
            except:
                pass          
                
            details['Editor Rating'] = editor_rating    
            details['Editor Ratings Count'] = editor_count             
            # Number of views
            views = ''
            try:
                views = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//span[@title='Views']"))).get_attribute('textContent').strip()
            except:
                pass          
                
            details['Number Of Views'] = views   
 
            # favorite count
            fav = ''
            try:
                fav = wait(driver, 2).until(EC.presence_of_element_located((By.XPATH, "//span[@title='Favorite count']"))).get_attribute('textContent').strip()
            except:
                pass          
                
            details['Favorite Count'] = fav    
            
            # appending the output to the datafame       
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except Exception as err:
            print(str(err))
           

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'yabookscentral.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_yabookscentral(path)


#!/usr/bin/env python

'''
    Given list of search queries, relies on GoogleAPI to search the web.
    Returns HTML contents of top or second result per query.
'''

from summarization_module import SummarizationGeminiModule

import re
import requests

from bs4 import BeautifulSoup
from bs4.element import Comment
from time import sleep

__version__ = '0.1.0'
__author__ = 'RK'

class WebSearchModule:
    def __init__(self, summarization_modele_api_key) -> None:
        self.search_result_urls_to_search_query = {}
        self.search_result_urls = set()
        self.search_result_url_to_html = {}
        self.search_query_to_search_content = {}
        self.smm = SummarizationGeminiModule(summarization_modele_api_key)

    # Return top search result contents
    def __search__(self, search_queries) -> dict:
        try:
            for search_query in search_queries:
                search_result = self.fetch_google_results(search_query)[0]
                if search_result == "":
                    search_result = self.fetch_google_results(search_query)[1]
                if search_result in self.search_result_urls:
                    self.search_result_urls_to_search_query[search_result].append(search_query)
                    search_result_html_content = self.search_result_url_to_html[search_result]
                else:
                    self.search_result_urls.add(search_result)
                    self.search_result_urls_to_search_query[search_result] = [search_query]
                    search_result_html_content = self.fetch_webpage_html(search_query, search_result)
                    self.search_result_url_to_html[search_result] = search_result_html_content
                
                if "Page Not Found" not in search_result_html_content:
                    self.search_result_url_to_html[search_result_html_content] = self.search_result_urls_to_search_query[search_result]
            
                self.search_query_to_search_content[search_query] = search_result_html_content
                
            return self.search_query_to_search_content
        except Exception as e:
            print(f"Encountered exception {e}")
            return self.search_query_to_search_content

    def fetch_google_results(self, search_query):
        URL = f"https://www.google.com/search?q={search_query}+"
        r = requests.get(URL) 
        soup = BeautifulSoup(r.content, 'html5lib')

        sleep(3)
    
        search_result_urls = []
        
        for a in soup.find_all('a', href=True):
            if "/url?q=http" in a['href'] and "google" not in a['href']:
                search_result_urls.append(a['href'].split("&sa=")[0].split("/url?q=")[-1])

        return search_result_urls
    
    def fetch_webpage_html(self, search_query, url):
        r = requests.get(url) 
        soup = BeautifulSoup(r.content, 'html.parser')
        if "Please enable Javascript" in soup:
            driver = webdriver.Firefox()
            driver.get(url)
            soup = driver.page_source
        #texts = soup.findAll(text=True)
        # kill all script and style elements
        for data in soup(["script", "style"]):
            data.extract()    # rip it out
        text = soup.get_text(separator='\n', strip=True)
        text = ' '.join(soup.stripped_strings)

        rgx_match = '"property(.*?)"'
        rgx_match_appState = '"(.*?)}'

        new_text = re.sub(rgx_match, '', text)
        new_text = re.sub(rgx_match_appState, '', text)

        if "nstream" in new_text:
            return ""
 
        summary = self.smm.summarize(search_query, new_text)
        return summary
        

    def tag_visible(self, element):
        if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True

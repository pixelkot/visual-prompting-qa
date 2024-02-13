#!/usr/bin/env python

"""
    SummarizationGeminiModule
    Uses Gemini to generate a summary of search_result_html, most relevant to the search_query.
    Return: str
"""

import google.generativeai as genai
import os

__version__ = '0.1.0'
__author__ = 'RK'

class SummarizationGeminiModule:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        genai.configure(api_key = api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    # TODO: Add GPT4's reason for search query as well
    def summarize(self, search_query: str, search_result_html: str):
        summarization_prompt =f"""Given a search query: {search_query}, summarize the most relevant information pertaining to the query from the following text in under 50 words: {search_result_html}"""
        
        response = self.model.generate_content(summarization_prompt)
        return response.text

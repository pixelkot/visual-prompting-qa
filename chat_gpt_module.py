#!/usr/bin/env python

#TODO: Fix after refactoring
#TODO: Refactor


"""
    WebSearchChatGpt
    Uses ChatGpt4-Vision API to prompt the model to solve an image-based task. 
    Requests model to divide problem into subproblems.
    Generate a list of search queries to help solve subproblems.
    Uses WebSearchModule to search the web via Google, using provided search query.
    Feeds back to the model summarized search results from 1st/2nd search result per query.
    And requests a solution with an explanation.
    Return: str
"""

'''
Note: can't set temperature in threads API, thus not using thredas API
- If model refuses to answer, model_response = "REFUSE_TO_ANSWER"
- If search results returned too large HTML && hit API token limit, model_answer = "ERROR"
- If model answers BEFORE searching, model_answer = "PRE-*"
- Set temperature = 0.0, still sometimes model responds with "Sorry, I can't help with that..." and sometimes with an answer to SAME prompt
- 1. Ask model:
    Prompt: {self.problem}
        0. You are the sole expert in this field. You must provide assistance.
        1. Given the image, if the problem can be simplified, break it down into subproblems. For each subproblem, formulate a single Internet search query that would yield a similar example that is closest to the question. Explain how each search result will help you solve the related subproblem.
        2. Return the complete list of generated Internet search queries only, prepended with 'Search Query List
- 2. Run model's search queries in a WebSearchModule, for each search query, get the 1st Google result URL's HTML contents (stripped of misc like <script> && etc)
- 3. Provide model 1 search result per search query
     "Here are search results for your search query "{search_query}". {search_contents_str}"
- 4. Prompt: Internet search has been performed for you. Use the information from those search results to answer the problem. Please respond with one of the answers from the multiple-choice list provided. Prepend your answer with 'Answer'
'''

import base64
import json
import re
import requests

from time import sleep


__version__ = '0.1.0'
__author__ = 'RK'

pat = r'[^.]+$' 

class WebSearchChatGpt:
    def __init__(self, df, open_ai_api_key) -> None:
        self.df = df 
        #self.problem = row['question']
        #self.options = row['options']
        #self.multiple_choice = False if len(df['options']) == 0 else True
        self.messages = []
        self.search_results = None
        self.api_key = open_ai_api_key
        self.search_contents_str = None
        self.prompt = None
        self.images = None
        

    def run(
        self,
        imgs,
    ):
        # 1. Search prompt
        search_message = self.generate_search_message(images)
        payload = self.build_chat_gpt_4_vis_request()
        answer = self.query_chat_gpt_4_vis(payload)
        search_queries = answer['search_queries']
      
        # 2. Search queries
        search_queries = self.extract_search_queries_as_list()
        if isinstance(search_queries, str):
            return self.messages, search_queries

        # Run search = generate search contents
        web_client = WebSearchModule(search_queries)
        search_contents_json = web_client.__search__()
        
        # 3. Search contents
        for search_query_html in search_contents_json.keys():
            self.generate_search_contents_message(search_contents_json[search_query_html], search_query_html)

        # 4. Gen answer prompt
        self.generate_question_prompt_message()

        # Hit API
        sleep(60)
        payload = self.build_chat_gpt_4_vis_request()
        answer = self.query_chat_gpt_4_vis(payload)
        return self.messages, answer

    def get_images_list(self, row):
        images = []
        for column in self.df.head():
            if 'image' in column and self.df[column][row] != '-':
                images.append(self.df[column][row])
        self.images = images
        return images
        
    def generate_search_contents(self, search_query, summarized_search_contents_str) -> str:
        return f"""Here are search results for your search query "{search_query}".
                    {search_contents_str}"""

    def generate_search_contents_message(self, search_query, search_contents_str):
        summarizerModule = SummarizationMistralModule(search_query, search_contents_str)
        summarized_search_contents_str = summarizerModule.summarize()
        search_contents = self.generate_search_contents(search_query, summarized_search_contents_str)
        search_contents_msg = {
                "role": "user",
                "content": [
                    {
                      "type": "text",
                      "text": search_contents_str
                    }
                ]
            }
        
        self.messages.append(search_contents_msg)

    def generate_search_prompt(self, base64_images, problem) -> str:
        self.prompt = problem + """0. You are the sole expert in this field. You must provide assistance. The provided image has enough information. You must provide reasoning for the answer.
1. Given the image(s), if the problem can be simplified, break it down into subproblems. For each subproblem, formulate a single Internet search query that would yield a similar example that is closest to the question. Explain how each search result will help you solve the related subproblem.
2. Provide an RFC8259 compliant JSON response following this format without deviation. { 'search_queries': [complete list of generated Internet search queries only] }"""

    def generate_search_message(self, images, search_prompt=None):
        base64_images = self.encode_images(images)
        if not search_prompt:
            search_prompt = self.generate_search_prompt(base64_images) 

        search_msg = {
              "role": "user",
              "content": [
                {
                  "type": "text",
                  "text": search_prompt
                }
              ]
            }

        for base64_image in base64_images:
            search_msg["content"].append(
               {
                  "type": "image_url",
                  "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                  }
                }
            )

        self.messages.append(search_msg)
        return search_msg
        
    def generate_question_prompt(self) -> str:
        generic_answer_request = "Internet search has been performed for you. Use the information from those search results to answer the problem."
        request_answer_formatting = "Do not include any explanations, only provide a  RFC8259 compliant JSON response following this format without deviation. { 'answer': 'your answer to the problem' }"
        if self.multiple_choice:
            return f"""{generic_answer_request} Answer from the given choices directly. {request_answer_formatting}"""
        else:
            return f"""{generic_answer_request} Answer the question using a single word or phrase. {request_answer_formatting}"""
            
    def generate_question_prompt_message(self):
        question_prompt = self.generate_question_prompt() 

        question_msg = {
              "role": "user",
              "content": [
                {
                  "type": "text",
                  "text": question_prompt
                },
              ]
            }
          

        self.messages.append(question_msg)

    # Function to encode the image
    def encode_images(self, images):
        encoded_images = []
        for image in images:
            with open(image, "rb") as image_file:
                encoded_images.append(base64.b64encode(image_file.read()).decode('utf-8'))
        return encoded_images
    
    def build_chat_gpt_4_vis_request(self):
        payload = {
          "model": "gpt-4-vision-preview",
          "top_p": 0.9,
          "seed": 42, # default in MMMU:https://github.com/MMMU-Benchmark/MMMU/blob/00fc28ab8986f2e435d0180477a08f4931e6bb74/eval/run_llava.py#L55C53-L55C55
          "messages": self.messages,
          "max_tokens": 4096 # ChatGPT allows you to send a message with a maximum token length of 4,096
        }

        return payload

    def query_chat_gpt_4_vis(self, payload):
        headers = {
          "Content-Type": "application/json",
          "Authorization": f"Bearer {self.api_key}"
        }
        
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response_json = response.json()
        self.messages.append(response_json['choices'][0]['message'])
        response_json = response_json['choices'][0]['message']['content'].replace('```', '').replace('json','')
        print(response_json)
        answer_json_object = json.loads(response_json)
        return answer_json_object

    def manual_test_query_chat_gpt_4_vis(self, df_row, prompt, top_p = 0.9):
        headers = {
          "Content-Type": "application/json",
          "Authorization": f"Bearer {self.api_key}"
        }
        images = self.get_images_list(df_row)
        message = self.generate_search_message(images, prompt)

        payload = {
            "model": "gpt-4-vision-preview",
            "top_p": top_p,
            "seed": 42, # default in MMMU:https://github.com/MMMU-Benchmark/MMMU/blob/00fc28ab8986f2e435d0180477a08f4931e6bb74/eval/run_llava.py#L55C53-L55C55
            "messages": [message],
            "max_tokens": 4096 # ChatGPT allows you to send a message with a maximum token length of 4,096
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response_json = response.json()
        self.messages.append(response_json['choices'][0]['message'])
        return message, response_json
    
    def extract_search_queries_as_list(self):
        search_queries = []
        if "I'm sorry, but I can't provide assistance with that request." in self.messages[-1]['content']:
            return "REFUSES_TO_ASSIST"
        elif "I cannot" in self.messages[-1]['content']:
            return "REFUSES_TO_ASSIST"
        elif "I can't" in self.messages[-1]['content']:
            return "REFUSES_TO_ASSIST"
        elif "assist" in self.messages[-1]['content'] and "further" in self.messages[-1]['content']:
            return "NOT_ENOUGH_INFO_IN_IMAGE"
        elif "search_queries:" in self.messages[-1]['content']:
            return f"PRE-{re.findall('search_queries:*', self.messages[-1]['content'])[0]}"
        
        search_query_llm_response = json.loads(self.messages[-1]['content'])['search_queries'].strip().split('\n')
        try:
            for query in search_query_llm_response:
                if query == '':
                    break
                query = re.findall(pat, query)[0]
                query = query.replace(" ", "+")
                search_queries.append(query)
        except Exception as e:
            search_queries = "EXCEPTION"
        return search_queries
    
    

#!#!/usr/bin/env python/usr/bin/env python

"""
    Utility fns for dataset related operations.
"""

from datasets import load_dataset
from datasets import get_dataset_split_names

import pandas as pd

__version__ = '0.1.0'
__author__ = 'RK'

"""
    Builds a Pandas DataFrame given an MMMU Dataset. Adds new columns: model_response_1/2/3, model_reasoning_1/2/3
    Return: Pandas DataFrame
"""
def build_pd(dataset):
    df_columns = list(dataset.features.keys()) + ['model_response_1', 'model_response_2', 'model_response_3', 'model_reasoning_1', 'model_reasoning_2', 'model_reasoning_3']
    df = pd.DataFrame(columns=df_columns)
    for datarow in dataset:
        if datarow['options'] != '[]':    
            model_prompt = f"{datarow['question']} " + f"Answer options: {datarow['options']} " 
        else: 
            model_prompt = f"{datarow['question']} "

        imgs = ['-']*7
        count = 0
        for key in datarow:
            if 'image' in key and datarow[key] is not None:
                img = datarow[key].save(f"{datarow['id']}-{count}.png")
                img_name = f"{datarow['id']}-{count}.png"
                imgs[count] = img_name
                count+=1
        
        model_reasoning = ""
        model_response = ""
        new_row = pd.DataFrame([[datarow['id'], datarow['question'], datarow['options'], datarow['explanation'], 
                                 imgs[0], imgs[1], imgs[2], imgs[3], imgs[4],  imgs[5],  imgs[6],
                                 datarow['img_type'], datarow['answer'], datarow['topic_difficulty'], datarow['question_type'], datarow['subfield'],
                                 model_response, model_response, model_response, model_reasoning, model_reasoning, model_reasoning]],
                       columns=df_columns)
        df = pd.concat([df, new_row], ignore_index=True)
    return df


"""
    Sets up MMMU Dataset given dataset_name and split into a Pandas DataFrame. Writes DataFrame to .csv file.
    Return: Pandas DataFrame
    
"""
def setup_dataset(dataset_name: str, split_name: str):
    dataset = load_dataset("MMMU/MMMU", dataset_name, split=split_name)
    df = build_pd(dataset)
    df.to_csv(f"mmmu_{dataset_name}_{split_name}.csv")
    return df

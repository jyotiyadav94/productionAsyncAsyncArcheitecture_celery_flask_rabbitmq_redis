import time
from celery import Celery
from celery.utils.log import get_task_logger
import yaml
import os
import sys
import torch
import json
import joblib
import numpy as np
import pandas as pd
from torch import nn
from transformers import BertTokenizer, BertModel, AdamW, get_linear_schedule_with_warmup

def get_device():
    # Get the device for PyTorch operations.
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")

class BERTClassifier(nn.Module):
    # BERT based classifier.
    def __init__(self, bert_model_name, num_classes):
        super(BERTClassifier, self).__init__()
        self.bert = BertModel.from_pretrained(bert_model_name)
        self.dropout = nn.Dropout(0.1)
        self.fc = nn.Linear(self.bert.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output
        x = self.dropout(pooled_output)
        logits = self.fc(x)
        return logits

def id2label_mapping(df, column_name):
    # Create a mapping from category IDs to labels.
    id2label = {i: label for i, label in enumerate(df[column_name].unique())}
    return id2label

# Module-level model and tokenizer initialization
bert_model_name = "bert-base-uncased"
num_labels = 25
model_path = "model.pth"
device = get_device()
id2label = {0: 'Household', 1: 'Dairy', 2: 'galletas', 3: 'Beverages', 4: 'Meat/Poultry/Seafood', 5: 'bombones', 6: 'Other', 7: 'AlcoholicBeverages', 8: 'Snacks/Candy', 9: 'Canned/JarredGoods', 10: 'PersonalCare', 11: 'FrozenFoods', 12: 'Pasta/Grains', 13: 'Bakery', 14: 'Prepared/Ready-Made Foods', 15: 'Toys: Other', 16: 'Prepared/Ready-Made_Foods', 17: 'Electronics', 18: 'Baby', 19: 'Pet', 20: 'FreshProduce', 21: 'Toys', 22: 'Produce', 23: 'Vitamins: Other', 24: 'Medicines: Household'}

model = BERTClassifier(bert_model_name, num_labels)
model.to(device)
model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
model.eval()

tokenizer = BertTokenizer.from_pretrained(bert_model_name)

def predict_category(text):
    max_length = 128
    encoding = tokenizer(text, return_tensors='pt', max_length=max_length, padding='max_length', truncation=True)
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        _, preds = torch.max(outputs, dim=1)
        
        # Return the label corresponding to the predicted numerical ID from id2label
        return id2label[preds.item()]

def preprocess(dict_request):
    processed_dict = {}
    for key, value in dict_request.items():
        processed_dict[key] = value.strip().lower()
    processed_string = ' '.join([f"{key}={value}" for key, value in processed_dict.items()])
    return processed_string

def form_response(dict_request):
    # Preprocess the input data
    input_data = preprocess(dict_request)
    print(input_data)
    # Get the prediction
    response = predict_category(input_data)
    return response


logger = get_task_logger(__name__)

app = Celery('tasks', 
                    broker='amqp://admin:mypass@rabbit:5672', 
                    backend='rpc://')

@app.task()
def elab_file(item_a, item_b):  
    logger.info('ASYNC POST /uploader > Got Request - Starting work')
    print(item_a)
    print(item_b)
    dict_req={'product_name': item_a, 'product_brand': item_b}
    logger.info('Preprocess Async Request')
    input_data = preprocess(dict_req)
    print("input_data",input_data)
    logger.info('predict Async Request')
    response = predict_category(input_data)
    print("response",response)
    logger.info('Work Finished ')
    return response

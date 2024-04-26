import os
import json
import random
import requests
import logging
import sqlalchemy
import urllib.parse
from sys import exit
from contextlib import asynccontextmanager
from pydantic import BaseModel
from sqlalchemy.sql import text
from fastapi import FastAPI, Query, status
from fastapi.logger import logger
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.declarative import declarative_base
from fastapi.middleware.cors import CORSMiddleware


DEBUG = False
DEMO_MODE = True
if ('DEBUG' in os.environ):
    DEBUG = os.environ['DEBUG']

# Logging
LOGLEVEL = os.environ.get('LOGLEVEL', 'DEBUG' if DEBUG else 'INFO').upper()
logger.setLevel(LOGLEVEL)


app = FastAPI(debug=True)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static", html=True), name="static")

class User(BaseModel):
    age: int
    annual_income: int
    emp_length: int
    loan_amount: int
    loan_intent: str = Query("PERSONAL", enum=["EDUCATION", "PERSONAL", "MEDICAL", "VENTURE",
                                                                        "HOMEIMPROVEMENT", "DEBTCONSOLIDATION"])
    home_ownership: str = Query("RENT", enum=["RENT", "OWN", "MORTGAGE"])

def triton_prediction(prediction_input):
    url = "http://localhost:8000/v2/models/rf_model/infer"
    if ('SCORING_URL' in os.environ):
       url = os.environ['SCORING_URL']
    payload = {
    "inputs": [
        {
        "name": "IN0",
        "shape": [
            1,
            11
        ],
        "datatype": "BYTES",
        "data": [
            prediction_input
        ]
        }
    ],
    "outputs": [
        {
        "name": "OUT0"
        }
    ]
    }

    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.post(url, json=payload)
    resposne_result = response.json()
    
    if resposne_result["outputs"]:
        return resposne_result["outputs"][0]["data"][0]
    else:
        print("Issue with Prediction")
        exit(16)

@app.post('/cra/predicttis')
async def triton_prediction_data(user:User):
    random_loan_percent_income = round(random.uniform(0.09, 0.63), 2)
    random_loan_grade = random.choice(["A", "B", "C", "D"])
    random_loan_int_rate = round(random.uniform(7.9, 13.47), 2)
    random_cb_person_default_on_file = random.choice(["Y", "N"])
    random_cb_person_cred_hist_length = random.randint(2, 20)
    my_data = {
        "person_age": user.age,
        "person_income": user.annual_income,
        "person_emp_length": user.emp_length,
        "person_home_ownership": user.home_ownership,
        "loan_intent": user.loan_intent,
        "loan_amnt": user.loan_amount,
        "loan_percent_income": random_loan_percent_income,
        "loan_grade": random_loan_grade,
        "loan_int_rate": random_loan_int_rate,
        "cb_person_default_on_file": random_cb_person_default_on_file,
        "cb_person_cred_hist_length": random_cb_person_cred_hist_length,
        "loan_status": -1
    }
    result = [my_data]

    input_data = [str(user.age), str(user.annual_income), str(user.home_ownership), str(user.emp_length), str(user.loan_intent), str(random_loan_grade), str(user.loan_amount), str(random_loan_int_rate), str(random_loan_percent_income), str(random_cb_person_default_on_file), str(random_cb_person_cred_hist_length)]

    headers = {'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,POST,PATCH,OPTIONS'}

    loan_val = triton_prediction(input_data)
    if loan_val:
        result[0]["loan_status"] = loan_val
    return JSONResponse(content=result, status_code=200, headers=headers)

import requests, json, os, httpx
# import pymupdf
import json_repair
import schemas
from uuid import uuid4
from pprint import pprint
from fastapi import status, HTTPException
from dotenv import load_dotenv
from datetime import datetime
# Load environment variables from .env file

load_dotenv()

TELEX_API_KEY = os.getenv('TELEX_API_KEY')
TELEX_API_URL = os.getenv('TELEX_API_URL')
TELEX_AI_URL = os.getenv('TELEX_AI_URL')
TELEX_AI_MODEL = os.getenv('TELEX_AI_MODEL')

class AIService:

    async def generate_search_queries(user_message: str, api_key: str):
        search_query_prompt = f"""
            Role: You are an expert at "Google Dorking." You excel at translating user requirements into a precise, effective search query for google's custom search api.

            Objective:
            Your primary task is to deeply analyze a user's natural language request to understand their underlying lead generation goal. 
            Based on this inferred goal, you will generate a powerful search query that can be used for google's custom search api to find leads that match the user's specific criteria.

            Input from User:
            The user's request is:

            {user_message}

            Output Requirements:

            1. You must provide your response only in the format of a JSON array of strings.

            2. Do not include any explanations or introductory text. Your entire response must be the raw JSON object.
        """

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                request_headers = {
                    "X-AGENT-API-KEY": api_key,
                    "X-MODEL": TELEX_AI_MODEL
                }

                request_body = {
                    # "organisation_id": "01971783-a2ff-78b2-bd02-d9ddf8fb23c6",
                    "model": "google/gemini-2.5-pro",
                    "messages": [
                        {
                        "role": "system",
                        "content": search_query_prompt
                        }
                    ],
                    "stream": False
                }
                print("TELEX AI URL", TELEX_AI_URL)

                response = await client.post(
                    TELEX_AI_URL, 
                    headers=request_headers,
                    json=request_body,
                    timeout=35.0
                )

                response.raise_for_status()
                # Extract the JSON string from the AI's response
                res = response.json().get("data", {}).get("Messages", None)
                reply = res.get("content", "not available")
                print("REPLY:")
                pprint(reply)
                
                fixed_json = json_repair.repair_json(reply, return_objects=True)
                print('FIXED:')
                pprint(fixed_json)
                return fixed_json

        except (KeyError, IndexError, json.JSONDecodeError, Exception) as e:
            print(f"Error parsing AI response: {e}") 
            print(f"Raw AI response was: {reply if reply is not None else "N/A"}")
            raise HTTPException(status_code=500, detail="Could not understand the AI model's response.")
        


    # async def generate_search_queries(user_message: str, api_key: str):
    #     search_query_prompt = f"""
    #         Role: You are an expert at "Google Dorking." You excel at translating user requirements into precise, effective search queries for google's custom search api.

    #         Objective:
    #         Your primary task is to deeply analyze a user's natural language request to understand their underlying lead generation goal. 
    #         Based on this inferred goal, you will generate a JSON array of diverse and powerful search queries for google's custon search api designed to find companies that match the user's specific criteria.

    #         Core Instructions:

    #         1. Deconstruct the Request: First, break down the user's request into its core components:

    #         - Target Entity: The type of company or organization (e.g., "tech startups," "restaurants," "hospitals").

    #         - Location: The geographical area (e.g., "Africa," "Lagos," "Cape Town").

    #         - Qualifier/Trigger Event: The specific condition, need, or event the user is targeting (e.g., "just got seed funding," "hiring a sales director," "don't have an online booking system").

    #         2. Select a Strategy: Based on the "Qualifier," choose the most effective search strategies.

    #         - If the goal is HIRING: Focus on job sites and company "Careers" pages. Use tactics like site:ng.indeed.com, site:linkedin.com/jobs, or intitle:"Careers" alongside the job role.

    #         - If the goal is GROWTH (e.g., funding, expansion): Focus on news sites and press releases. IMPORTANT: The after: operator is invalid. To find recent results, include the current year (2025) or previous year (2024) as keywords, or use action words like "raises," "acquires," or "launches."

    #         - If the goal is finding a LACK of a feature: Use a "negative search" with the minus operator (-) to exclude pages that mention the feature. For example: "[industry]" "[location]" -inurl:"order" -intitle:"online ordering".

    #         - If the goal is GENERAL prospecting: Use foundational queries like direct search ("[industry] in [location]"), directory searches, and finding "listicles" ("list of top [industry]").

    #         Input from User:
    #         The user's request is:

    #         {user_message}

    #         Output Requirements:

    #         1. You must provide your response only in the format of a JSON array of strings.

    #         2. Do not include any explanations or introductory text. Your entire response must be the raw JSON object.

    #         3. Generate between 5 and 8 diverse queries that reflect different, creative angles to achieve the user's specific goal.

    #         Example Scenarios:

    #         Example 1: User wants companies that are actively hiring.

    #         User Request: Find me e-commerce companies in Nigeria that are hiring logistics managers.

    #         Expected AI Output:

    #         JSON
    #         [
    #             "site:ng.indeed.com \"e-commerce\" \"logistics manager\" \"Lagos\"",
    #             "site:linkedin.com/jobs \"e-commerce\" \"logistics manager\" Nigeria",
    #             "intitle:\"careers\" OR intitle:\"vacancies\" \"e-commerce\" \"logistics manager\" Nigeria",
    #             "\"e-commerce companies in Nigeria\" AND \"we are hiring a logistics manager\"",
    #             "\"Konga\" OR \"Jumia\" \"logistics manager\" vacancy",
    #             "\"Head of Logistics\" job e-commerce Nigeria"
    #         ]
    #         Example 2: User wants companies that recently received funding (Corrected).

    #         User Request: Fintech startups in Africa that announced seed funding recently.

    #         Expected AI Output:

    #         JSON
    #         [
    #             "site:techcabal.com OR site:disrupt-africa.com fintech \"seed funding\" 2025 OR 2024",
    #             "African fintech startup raises seed round 2025",
    #             "\"pre-seed funding\" fintech \"Nairobi\" OR \"Lagos\" OR \"Cape Town\" 2024",
    #             "site:techcrunch.com \"Africa\" \"fintech\" \"seed\" 2025",
    #             "intitle:\"raises\" OR intitle:\"secures\" fintech Africa seed funding"
    #         ]
    #         Example 3: User wants general information.

    #         User Request: list of private hospitals in Abuja

    #         Expected AI Output:

    #         JSON
    #         [
    #             "\"private hospitals in Abuja\"",
    #             "\"list of accredited private hospitals Abuja\"",
    #             "site:linkedin.com/company \"private hospital\" \"Abuja\"",
    #             "\"best hospitals in Abuja, Nigeria\"",
    #             "directory of private healthcare facilities FCT Abuja"
    #         ]

    #     """

    #     try:
    #         async with httpx.AsyncClient(timeout=5.0) as client:
    #             request_headers = {
    #                 "X-AGENT-API-KEY": api_key,
    #                 "X-MODEL": TELEX_AI_MODEL
    #             }
    #             print(f"Request headers: {request_headers}")

    #             request_body = {
    #                 # "organisation_id": "01971783-a2ff-78b2-bd02-d9ddf8fb23c6",
    #                 "model": "google/gemini-2.5-pro",
    #                 "messages": [
    #                     {
    #                     "role": "system",
    #                     "content": search_query_prompt
    #                     }
    #                 ],
    #                 "stream": False
    #             }

    #             response = await client.post(
    #                 TELEX_AI_URL, 
    #                 headers=request_headers,
    #                 json=request_body,
    #                 timeout=30.0
    #             )

    #             pprint(response.json())
    #             response.raise_for_status()
    #             # Extract the JSON string from the AI's response
    #             res = response.json().get("data", {}).get("Messages", None)
    #             reply = res.get("content", "not available")
    #             pprint(reply)
                
    #             fixed_json = json_repair.repair_json(reply, return_objects=True)
    #             pprint(fixed_json)
    #             return fixed_json

    #     except (KeyError, IndexError, json.JSONDecodeError, Exception) as e:
    #         print(f"Error parsing AI response: {e}")
    #         print(f"Raw AI response was: {reply}")
    #         raise HTTPException(status_code=500, detail="Could not understand the AI model's response.")



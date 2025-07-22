import os, httpx, requests, time
from pprint import pprint
import uvicorn, json
import schemas
from uuid import uuid4
from fastapi import FastAPI, Request, status, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from a2a.utils import new_agent_text_message
from dotenv import load_dotenv
from services import AIService
# Load environment variables from .env file

load_dotenv()

TELEX_API_KEY = os.getenv('TELEX_API_KEY')
TELEX_API_URL = os.getenv('TELEX_API_URL')
TELEX_AI_URL = os.getenv('TELEX_AI_URL')
TELEX_AI_MODEL = os.getenv('TELEX_AI_MODEL')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_SEARCH_ENGINE_ID = os.getenv('GOOGLE_SEARCH_ENGINE_ID')

app = FastAPI()

RAW_AGENT_CARD_DATA = {
  "name": "Lead research Agent",
  "description": "An agent that...",
  "url": "",
  "provider": {
      "organization": "Telex Org.",
      "url": "https://telex.im"
    },
  "version": "1.0.0",
  "documentationUrl": "",
  "capabilities": {
    "streaming": True,
    "pushNotifications": True
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [
    {
      "id": "convo",
      "name": "Conversation",
      "description": "Responds to user input with meaningful related output.",
      "inputModes": ["text"],
      "outputModes": ["text"],
      "examples": [
        {
          "input": { "parts": [{ "text": "Hello", "contentType": "text/plain" }] },
          "output": { "parts": [{ "text": "Hi, how are you?", "contentType": "text/plain" }] }
        }
      ]
    }
  ]
}


@app.get("/", response_class=HTMLResponse)
def read_root():
    return '<p style="font-size:30px">Prospect research agent</p>'


@app.get("/.well-known/agent.json")
def agent_card(request: Request):
    external_base = request.headers.get("x-external-base-url", "")
    current_base_url = str(request.base_url).rstrip("/") + external_base

    response_agent_card = RAW_AGENT_CARD_DATA.copy()

    response_agent_card["url"] = current_base_url
    response_agent_card["provider"]["url"] = current_base_url
    response_agent_card["provider"]["documentationUrl"] = f"{current_base_url}/docs"

    return response_agent_card


async def handle_task(message:str, request_id, user_id:str, task_id: str, webhook_url: str, api_key: str):

  queries = await AIService.generate_search_queries(user_message=message, api_key=api_key)
  print("queries", queries)

  results = {}
  for i in range(0,len(queries)):
    search_query = queries[i]

    # Construct the API request URL
    url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_SEARCH_ENGINE_ID}&q={search_query}&num=10"

    # Make the request
    response = requests.get(url)
    search_results = response.json()

    if 'items' in search_results:
        for item in search_results['items']:
            business_title = item.get('title')
            website_url = item.get('link') 

            results[business_title] = website_url

        time.sleep(1) 
    else:
        print("No results found or an error occurred.")
        print(search_results)
    
  
  print("SEARCH RESULTS")
  pprint(results)

  markdown = "\n".join(
    f"{i + 1}. [{title}]({url})"
    for i, (title, url) in enumerate(results.items())
  )

  parts = schemas.TextPart(text=markdown)

  message = schemas.Message(role="agent", parts=[parts])

  artifacts = schemas.Artifact(parts=[parts])

  task = schemas.Task(
    id = task_id,
    status =  schemas.TaskStatus(
      state=schemas.TaskState.COMPLETED, 
      message=schemas.Message(role="agent", parts=[schemas.TextPart(text="Success!")])
    ),
    artifacts = [artifacts]
  )

  webhook_response = schemas.SendResponse(
      id=request_id,
      result=task
  )

  pprint(webhook_response.model_dump())


  async with httpx.AsyncClient() as client:
    headers = {"X-TELEX-API-KEY": api_key}
    is_sent = await client.post(webhook_url, headers=headers,  json=webhook_response.model_dump(exclude_none=True))
    pprint(is_sent.json())

  print("background done")
  return 



@app.post("/")
async def handle_request(request: Request, background_tasks: BackgroundTasks):
  #message that comes in should be the search query
  try:
    body = await request.json()

  except json.JSONDecodeError as e:
    error = schemas.JSONParseError(
      data = str(e)
    )
    response = schemas.JSONRPCResponse(
       error=error
    )

  request_id = body.get("id")
  user_id = body["params"]["message"]["metadata"].get("telex_user_id", None)  
  org_id = body["params"]["message"]["metadata"].get("org_id", None)  
  webhook_url = body["params"]["configuration"]["pushNotificationConfig"]["url"]
  api_key = body["params"]["configuration"]["pushNotificationConfig"]["authentication"].get("credentials", TELEX_API_KEY)

  message_parts = body["params"]["message"]["parts"]

  if not message_parts:
    raise HTTPException(
      status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
      detail="Message cannot be empty."
    )

  new_task = schemas.Task(
    id = uuid4().hex,
    status =  schemas.TaskStatus(
      state=schemas.TaskState.SUBMITTED, 
      message=schemas.Message(role="agent", parts=[schemas.TextPart(text="In progress")])
    )
  )

  incoming_message: schemas.Part = message_parts[0]

  print(incoming_message, "message")

  text_message = incoming_message.get("text", None)

  if not text_message:
    raise HTTPException(
      status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
      detail="Message text cannot be empty."
    )

  background_tasks.add_task(handle_task, text_message, request_id, user_id, new_task.id, webhook_url, api_key)

  response = schemas.JSONRPCResponse(
      id=request_id,
      result=new_task
  )

  response = response.model_dump(exclude_none=True)
  pprint(response)
  return response


if __name__ == "__main__":
    port = int(os.getenv("PORT", 4000))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)

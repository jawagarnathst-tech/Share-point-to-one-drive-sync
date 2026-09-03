from fastapi import FastAPI, Request, Response, BackgroundTasks
from app.config import settings
from app.sync import process_delta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/sharepoint/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    # Validation request from Microsoft Graph
    validation_token = request.query_params.get("validationToken")
    if validation_token:
        return Response(content=validation_token, media_type="text/plain", status_code=200)

    # Process notification
    body = await request.json()
    logger.info(f"Received webhook: {body}")
    
    # Normally we would validate clientState here for each notification
    # if "clientState" not in body.get("value", [{}])[0] or body["value"][0]["clientState"] != settings.webhook_client_state:
    #     return Response(status_code=403)

    # Enqueue delta processing as a background task
    background_tasks.add_task(process_delta)
    
    return Response(status_code=202)

from pydantic import BaseModel

class ApifyEventData(BaseModel):
    actorRunId: str
    defaultDatasetId: str | None = None

class ApifyWebhookPayload(BaseModel):
    eventType: str
    eventData: ApifyEventData

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from services.scraper import scrape_google_maps

app = FastAPI()

class ScrapeRequest(BaseModel):
    industry: str
    locations: List[str]
    limit_per_location: Optional[int] = 5

# NOTICE: strictly 'def', NOT 'async def'
@app.post("/scrape")
def run_scraper(request: ScrapeRequest):
    """
    Synchronous endpoint. 
    FastAPI runs this in a threadpool, so it won't block the server.
    """
    all_leads = []
    
    for loc in request.locations:
        # NOTICE: No 'await' here
        leads = scrape_google_maps(
            industry=request.industry, 
            location=loc, 
            total=request.limit_per_location
        )
        all_leads.extend(leads)
    
    return {
        "status": "success", 
        "total": len(all_leads), 
        "data": all_leads
    }
# run.py
import uvicorn
import asyncio
import sys

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    uvicorn.run("app.main:app", reload=True)
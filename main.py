# main.py

from fastapi import FastAPI
from routes import router  # if file is route.py in same directory
# from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
# import uvicorn


app = FastAPI(
    title="Chatbot User API",
    version="1.0.0"
)
# Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://13.127.57.5:5177"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router
app.include_router(router)

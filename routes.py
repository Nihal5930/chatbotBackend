import time
import uuid

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, HTTPException, Body
from models import User
from dynamodb import table
from pydantic import BaseModel
import boto3
import json
from typing import Dict, Optional
import requests
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
chat_table = dynamodb.Table('Chat')

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

router = APIRouter()


@router.post("/users", status_code=201)
def create_user(user: User = Body(...)):
    try:
        response = table.get_item(Key={"emailID": user.emailID})
        if "Item" in response:
            return {"status": "ok",
                    "message": "User already registered"}
        table.put_item(
            Item=user.dict()
        )
        return {"status": "ok",
                "message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users")
def get_all_users():
    try:
        response = table.scan()
        return response.get("Items", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{emailID}")
def update_user(emailID: str, payload: dict):
    history = payload.get("conversationHistory")
    if history is None:
        raise HTTPException(status_code=400, detail="Missing conversationHistory")
    try:
        response = table.update_item(
            Key={"emailID": emailID},
            UpdateExpression="SET conversationHistory = :h",
            ExpressionAttributeValues={":h": history},
            ReturnValues="UPDATED_NEW"
        )
        return {"message": "User history updated", "updated": response["Attributes"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MessageRequest(BaseModel):
    user: Dict
    message: str
    chat_id: Optional[str] = None

@router.post("/chat")
def chat_with_llama(req: MessageRequest):
    # print(req)
    chat_id = req.chat_id or str(uuid.uuid4())
    user_id = req.user.get("sub", "anonymous")

    # Call Together API
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "messages": [
            {"role": "user", "content": req.message}
        ]
    }
    response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=data)

    if response.status_code != 200:
        return {"error": response.text}

    ai_reply = response.json()["choices"][0]["message"]["content"]

    # Prepare new messages
    new_messages = [
        {"sender": "user", "message": req.message, "timestamp": str(time.time())},
        {"sender": "ai", "message": ai_reply, "timestamp": str(time.time())}
    ]

    try:
        # Try to get existing chat thread
        existing = chat_table.get_item(Key={"chat_id": chat_id})

        if "Item" in existing:
            updated_messages = existing["Item"]["messages"] + new_messages
            chat_table.update_item(
                Key={"chat_id": chat_id},
                UpdateExpression="SET messages = :msgs",
                ExpressionAttributeValues={":msgs": updated_messages}
            )
        else:
            # Create new item
            chat_table.put_item(Item={
                "chat_id": chat_id,
                "user_id": user_id,
                "messages": new_messages
            })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "chat_id": chat_id,
        "reply": ai_reply
    }


@router.get("/chat/{chat_id}")
def get_chat(chat_id: str):
    try:
        item = chat_table.get_item(Key={"chat_id": chat_id})
        if "Item" in item:
            return item["Item"]
        return {"error": "Chat not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/chats/{user_id}")
def get_all_chats_for_user(user_id: str):
    try:
        response = chat_table.query(
            IndexName="user_id-index",  # GSI on user_id
            KeyConditionExpression=Key("user_id").eq(user_id)
        )
        items = response.get("Items", [])
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/users/active")
def get_active_users():
    try:
        # Step 1: Scan Chat table to get all user_ids
        chat_response = chat_table.scan()
        chat_items = chat_response.get("Items", [])

        # Extract unique user_ids from the chat table
        user_ids = {item["user_id"] for item in chat_items if "user_id" in item}
        # print(user_ids)
        # Step 2: Fetch user details from ChatbotUsers table
        users_data = []
        for user_id in user_ids:
            # print(user_id)
            response = table.get_item(Key={"sub-index": user_id})  # assuming user_id is emailID
            if "Item" in response:
                users_data.append(response["Item"])

        return {"active_users": users_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

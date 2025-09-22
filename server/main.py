from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks, Query
from model.model import connect_to_db, close_db_connection, User
import uvicorn
from model.model import Batch, User, Call, CallStatus
import os

from utils.document import read_xlsx_file

from utils.call_executor import CallExecutor
from utils.vapi_client import VAPIClient
from loguru import logger
from bson import ObjectId
from datetime import datetime

from utils.tools import handle_tool_call, get_near_by_clinic_data
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fastapi import Response

# Environment variables
CUSTOM_DOMAIN = os.getenv("BASE_URL", "https://your-domain.com")
VAPI_STORAGE_DOMAIN = "https://storage.vapi.ai"
EN_HI_ASSISTANT_ID = os.getenv("EN_HI_ASSISTANT_ID")
TAMIL_ASSISTANT_ID = os.getenv("TAMIL_ASSISTANT_ID")
CUSTOM_ASSISTANT_URL = os.getenv("CUSTOM_ASSISTANT_URL")


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    """
    Initialize database connection on application startup.
    Uses Motor async client for better performance and reliability.
    """
    logger.info("🟢🟢Connecting to MongoDB")
    await connect_to_db()


@app.on_event("shutdown")
async def shutdown_db_client():
    """
    Close database connection gracefully on application shutdown.
    This ensures proper cleanup of resources.
    """
    logger.info("🔴 Shutting down MongoDB connection")
    await close_db_connection()


@app.get("/")
async def root():
    try:
        # Group pincode data by city and store in KnowledgeBase
        from utils.tools import handle_vector_search_tool
        result = await handle_vector_search_tool({"query": "can you provide customer support number?"})
        # result = await get_near_by_clinic_data(city="Chennai",pincode="600001")
        return {"message": "Hello World", "result": result}
    except Exception as e:
        logger.error(f"Error in root endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/upload")
async def upload_file(file: UploadFile = File(...), assistant_code: str = Query(None)):
    """
    Upload Excel file locally and extract user data
    """
    # Validate file type
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed"
        )

    # Create uploads directory if it doesn't exist
    os.makedirs("uploads", exist_ok=True)

    # Generate unique filename to avoid conflicts
    import uuid

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = f"uploads/{unique_filename}"

    try:
        # Save file locally
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Extract users from Excel file using the local path
        users = read_xlsx_file(file_path)

        # save file to database
        batch = Batch(file_name=file.filename, url=file_path)
        await batch.save()

        # Create all call objects in batch
        calls = []
        for user in users:
            call = Call(batch_id=str(batch.id), status=CallStatus.PENDING, user=user)
            calls.append(call)

        # Batch insert all calls at once
        await Call.insert_many(calls)

        # Since batch_id is stored as DBRef, we need to query using the batch object
        calls_with_ids = await Call.find(Call.batch_id == str(batch.id)).to_list()
        logger.info(f"🔍 Found {len(calls_with_ids)} calls for batch {batch.id}")
        
        # Select assistant ID or custom URL based on assistant_code
        assistant_id = None
        custom_url = None
        if assistant_code:
            if assistant_code.lower() == "en-hi":
                assistant_id = EN_HI_ASSISTANT_ID
                logger.info(f"🌐 Selected EN-HI assistant: {assistant_id}")
            elif assistant_code.lower() == "tamil":
                assistant_id = TAMIL_ASSISTANT_ID
                logger.info(f"🌐 Selected Tamil assistant: {assistant_id}")
            elif assistant_code.lower() == "custom":
                custom_url = CUSTOM_ASSISTANT_URL
                logger.info(f"🌐 Selected Custom URL: {custom_url}")
            else:
                logger.warning(f"⚠️ Unknown assistant_code: {assistant_code}. No assistant will be used.")
        else:
            logger.warning("⚠️ No assistant_code provided. No assistant will be used.")
        
        if not assistant_id and not custom_url:
            raise HTTPException(
                status_code=400, 
                detail=f"No valid assistant ID or custom URL found for assistant_code: {assistant_code}. Please provide 'en-hi', 'tamil', or 'custom'."
            )
        
        call_executor = CallExecutor(vapi_client=VAPIClient())
        responses = []

        # initiate all calls
        for call in calls_with_ids[:10]:
            if custom_url:
                # Use custom call function
                res = await call_executor.execute_custom_call(call_data=call, custom_url=custom_url)
            else:
                # Use regular VAPI call
                res = await call_executor.execute_call(call_data=call, assistant_id=assistant_id)
            responses.append(res)

        return {
            "message": "File uploaded and processed successfully",
            "original_filename": file.filename,
            "saved_path": file_path,
            "total_users": len(users),
            "call_result": responses,
            "calls": calls_with_ids,
        }

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        # Clean up file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


from utils.events import handle_call_completion, handle_call_started


@app.post("/vapi/webhooks/call-events")
async def handle_call_events(request: Request, background_tasks: BackgroundTasks):
    """Handle VAPI call events webhook"""
    try:
        # Log all incoming webhook requests
        headers = dict(request.headers)
        client_ip = request.client.host if request.client else "unknown"

    

        webhook_data = await request.json()

        # Extract event type from nested structure
        message_data = webhook_data.get("message", {})
        event_type = message_data.get("type", "unknown")

        # Also check for direct type field as fallback
        if event_type == "unknown":
            event_type = webhook_data.get("type", "unknown")

        logger.info(f"📞 VAPI webhook type: {event_type}")

        # Return immediately and process in background for long-running operations
        if event_type in ["call.completed", "call.ended", "end-of-call-report"]:
            logger.info(f"🎯 Queuing {event_type} webhook for background processing")
            background_tasks.add_task(handle_call_completion, webhook_data)
            return {
                "status": "received",
                "event_type": event_type,
                "message": "Webhook queued for background processing",
            }
        elif event_type == "call.started":
            logger.info("🎯 Processing call.started webhook immediately")
            return await handle_call_started(webhook_data)
        else:
            logger.warning(f"⚠️ Unhandled webhook event type: {event_type}")
            return {
                "status": "received",
                "event_type": event_type,
                "message": "Event type not handled",
            }

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}")
        import traceback

        logger.error(f"📍 Full traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}


@app.get("/batches")
async def get_all_batches():
    """
    Get all batches sorted by creation date (latest first)
    """
    try:
        # Find all batches sorted by created_at in descending order (latest first)
        batches = await Batch.find_all().sort("-created_at").to_list()

        # Convert batches to dict format for JSON response
        batches_data = []
        for batch in batches:
            batch_dict = {
                "id": str(batch.id),
                "file_name": batch.file_name,
                "url": batch.url,
                "created_at": batch.created_at.isoformat(),
            }
            batches_data.append(batch_dict)

        return {"total_batches": len(batches_data), "batches": batches_data}

    except Exception as e:
        logger.error(f"Error fetching all batches: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching batches: {str(e)}")


@app.get("/calls/batch/{batch_id}")
async def get_calls_by_batch(batch_id: str):
    """
    Get all calls for a specific batch ID
    """
    try:
        # Find all calls with the given batch_id
        calls = await Call.find(Call.batch_id == batch_id).to_list()

        if not calls:
            raise HTTPException(
                status_code=404, detail=f"No calls found for batch ID: {batch_id}"
            )

        # Convert calls to dict format for JSON response
        calls_data = []
        for call in calls:
            call_dict = {
                "id": str(call.id),
                "batch_id": call.batch_id,
                "status": call.status,
                "user": {
                    "name": call.user.name,
                    "email": call.user.email,
                    "phone": call.user.phone,
                },
                "call_id": call.vapi_call_id,
                "call_result": call.call_result.dict() if call.call_result else None,
                "created_at": call.created_at.isoformat(),
                "updated_at": call.updated_at.isoformat(),
            }
            calls_data.append(call_dict)

        return {
            "batch_id": batch_id,
            "total_calls": len(calls_data),
            "calls": calls_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching calls for batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching calls: {str(e)}")


@app.post("/calls/{call_id}/redial")
async def redial_call(call_id: str, assistant_code: str = Query(None)):
    """
    Redial a call by call ID
    - Clears existing call result
    - Executes the call again using CallExecutor
    - Updates call status and returns success
    """
    try:
        logger.info(f"🔄 Starting redial process for call ID: {call_id}")

        # Validate call_id
        if not call_id or call_id == "undefined" or call_id == "null":
            logger.error(f"❌ Invalid call ID provided: {call_id}")
            raise HTTPException(status_code=400, detail="Invalid call ID provided")

        # Validate ObjectId format
        try:
            object_id = ObjectId(call_id)
        except Exception as e:
            logger.error(
                f"❌ Invalid ObjectId format for call_id: {call_id}, error: {e}"
            )
            raise HTTPException(
                status_code=400, detail=f"Invalid call ID format: {call_id}"
            )

        # Find the call record
        call_record = await Call.find_one({"_id": object_id})
        if not call_record:
            logger.error(f"❌ Call not found with ID: {call_id}")
            raise HTTPException(
                status_code=404, detail=f"Call not found with ID: {call_id}"
            )

        logger.info(f"✅ Found call record: {call_record.id}")
        logger.info(
            f"📞 Call details - User: {call_record.user.name}, Phone: {call_record.user.phone}"
        )

        # Clear existing call result and set status to redialed
        logger.info(f"🧹 Clearing existing call result for call: {call_id}")
        await call_record.update(
            {
                "$set": {
                    "call_result": None,
                    "status": "redialed",
                    "vapi_call_id": None,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        logger.info(f"✅ Cleared call result and set status to redialed")

        # Select assistant ID or custom URL based on assistant_code
        assistant_id = None
        custom_url = None
        if assistant_code:
            if assistant_code.lower() == "en-hi":
                assistant_id = EN_HI_ASSISTANT_ID
                logger.info(f"🌐 Selected EN-HI assistant: {assistant_id}")
            elif assistant_code.lower() == "tamil":
                assistant_id = TAMIL_ASSISTANT_ID
                logger.info(f"🌐 Selected Tamil assistant: {assistant_id}")
            elif assistant_code.lower() == "custom":
                custom_url = CUSTOM_ASSISTANT_URL
                logger.info(f"🌐 Selected Custom URL: {custom_url}")
            else:
                logger.warning(f"⚠️ Unknown assistant_code: {assistant_code}. No assistant will be used.")
        else:
            logger.warning("⚠️ No assistant_code provided. No assistant will be used.")
        
        if not assistant_id and not custom_url:
            raise HTTPException(
                status_code=400, 
                detail=f"No valid assistant ID or custom URL found for assistant_code: {assistant_code}. Please provide 'en-hi', 'tamil', or 'custom'."
            )

        # Execute the call using CallExecutor
        logger.info(f"🚀 Executing redial for call: {call_id}")
        call_executor = CallExecutor(vapi_client=VAPIClient())

        if custom_url:
            # Use custom call function
            success, vapi_call_id, error_message = await call_executor.execute_custom_call(
                call_record, custom_url=custom_url
            )
        else:
            # Use regular VAPI call
            success, vapi_call_id, error_message = await call_executor.execute_call(
                call_record, assistant_id=assistant_id
            )

        # Update the call with the new vapi_call_id if successful
        if success and vapi_call_id:
            logger.info(f"📞 Updating call with new VAPI call ID: {vapi_call_id}")
            await call_record.update(
                {
                    "$set": {
                        "vapi_call_id": vapi_call_id,
                        "updated_at": datetime.utcnow(),
                    }
                }
            )

        if success and vapi_call_id:
            logger.success(f"✅ Redial successful for call: {call_id}")
            logger.success(f"📞 New VAPI call ID: {vapi_call_id}")

            return {
                "status": "success",
                "message": "Call redialed successfully",
                "call_id": call_id,
                "call_id": vapi_call_id,
            }
        else:
            logger.error(f"❌ Redial failed for call: {call_id}")
            logger.error(f"❌ Error: {error_message}")

            # Update call status to failed
            await call_record.update(
                {"$set": {"status": CallStatus.FAILED, "updated_at": datetime.utcnow()}}
            )

            raise HTTPException(
                status_code=500, detail=f"Failed to redial call: {error_message}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in redial endpoint: {e}")
        import traceback

        logger.error(f"📍 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error redialing call: {str(e)}")



@app.get("/media/{path:path}")
async def proxy_media(path: str):
    # Use VAPI storage domain for proxying, but serve through custom domain
    url = f"{VAPI_STORAGE_DOMAIN}/{path}"
    logger.info(f"🔍 Proxying media: {url}")
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Referer": f"{VAPI_STORAGE_DOMAIN}/"})
    
    # Pass through the original content with headers
    return Response(
        content=r.content,
        media_type=r.headers.get("content-type")
    )



@app.post("/vapi/tools")
async def vapi_tools(request: Request):
    """VAPI tools handler - processes tool calls from VAPI"""

    try:
        data = await request.json()
        logger.info(f"🔧 VAPI tools handler received: {data}")

        # Extract message data from the request
        message_data = data.get("message", {})
        event_type = message_data.get("type", "")

        # Check if this is a tool-calls event
        if event_type == "tool-calls":
            logger.info("🎯 Processing tool-calls event")

            # Extract tool call list
            tool_call_list = message_data.get("toolCallList", [])
            tool_with_tool_call_list = message_data.get("toolWithToolCallList", [])

            logger.info(f"📋 Found {len(tool_call_list)} tool calls")
            logger.info(f"📋 Tool call list: {tool_call_list}")
            logger.info(f"📋 Tool with tool call list: {tool_with_tool_call_list}")

            # Process each tool call
            results = []
            for i, tool_call_data in enumerate(tool_with_tool_call_list):
                logger.info(
                    f"🔧 Processing tool call {i+1}/{len(tool_with_tool_call_list)}"
                )
                logger.info(f"🔧 Tool call data structure: {tool_call_data}")

                # Handle the tool call
                result = await handle_tool_call(tool_call_data)
                results.append(result)

                logger.info(
                    f"✅ Tool call {i+1} completed with result length: {len(result.get('result', ''))}"
                )
            logger.info(f"🔧 🚀🚀🚀🚀🚀 Results: {results}")
            return {"results": results}

        else:
            logger.warning(f"⚠️ Unhandled event type: {event_type}")
            return {
                "status": "ignored",
                "message": f"Event type '{event_type}' not handled by tools endpoint",
            }

    except Exception as e:
        logger.error(f"❌ Error in VAPI tools handler: {e}")
        import traceback

        logger.error(f"📍 Full traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}






@app.post("/custom-assistant-webhook")
async def custom_assistant_webhook(request: Request):
    """Handle custom assistant webhook for call status updates"""
    try:
        # Log incoming webhook
        headers = dict(request.headers)
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"📞 Custom Assistant Webhook received from {client_ip}")
        logger.info(f"📋 Headers: {headers}")

        # Parse webhook data
        webhook_data = await request.json()
        logger.info(f"📦 Webhook payload: {webhook_data}")

        # Extract required fields
        call_sid = webhook_data.get("call_sid")
        status = webhook_data.get("status")
        phone_number = webhook_data.get("phone_number")
        name = webhook_data.get("name")
        transcript = webhook_data.get("transcript", "")
        recording_url = webhook_data.get("recording_url", "")
        call_cost = webhook_data.get("call_cost", 0.0)
        created_at = webhook_data.get("created_at")
        updated_at = webhook_data.get("updated_at")

        # Validate required fields
        if not call_sid:
            logger.error("❌ Missing call_sid in webhook payload")
            raise HTTPException(status_code=400, detail="Missing call_sid")

        if not status:
            logger.error("❌ Missing status in webhook payload")
            raise HTTPException(status_code=400, detail="Missing status")

        logger.info(f"🔍 Processing webhook for call_sid: {call_sid}")
        logger.info(f"📊 Status: {status}")
        logger.info(f"📞 Phone: {phone_number}")
        logger.info(f"👤 Name: {name}")

        # Find call record by vapi_call_id (which stores call_sid for custom calls)
        call_record = await Call.find_one(Call.vapi_call_id == call_sid)
        
        if not call_record:
            logger.error(f"❌ Call record not found for call_sid: {call_sid}")
            raise HTTPException(status_code=404, detail=f"Call record not found for call_sid: {call_sid}")

        logger.info(f"✅ Found call record: {call_record.id}")

        # Map custom status to CallStatus enum
        status_mapping = {
            "call_initiated": CallStatus.INITIATED,
            "ringing": CallStatus.INITIATED,
            "in_progress": CallStatus.IN_PROGRESS,
            "active": CallStatus.ACTIVE,
            "completed": CallStatus.COMPLETED,
            "done": CallStatus.DONE,
            "ended": CallStatus.ENDED,
            "cancelled": CallStatus.CANCELLED,
            "failed": CallStatus.FAILED,
            "no_show": CallStatus.NO_SHOW,
            "terminated": CallStatus.TERMINATED
        }

        mapped_status = status_mapping.get(status.lower(), CallStatus.COMPLETED)
        logger.info(f"🔄 Mapped status: {status} -> {mapped_status}")

        # Prepare call_result data
        call_result_data = {
            "transcript": transcript,
            "recording_url": recording_url,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        # Update call record
        update_data = {
            "status": mapped_status,
            "call_result": call_result_data,
            "updated_at": datetime.utcnow()
        }

        await call_record.update({"$set": update_data})
        logger.success(f"✅ Updated call record {call_record.id} with status: {mapped_status}")

        # Trigger analysis if transcript is available
        if transcript and len(transcript.strip()) > 0:
            logger.info(f"🔍 Triggering analysis for call {call_record.id}")
            try:
                from utils.analyst import analyze_transcript
                analysis_result = analyze_transcript(transcript)
                
                # Update call_result with analysis
                analysis_data = {
                    "summary": analysis_result.summary,
                    "quality_score": analysis_result.quality_score,
                    "customer_intent": analysis_result.customer_intent,
                    "updated_at": datetime.utcnow()
                }
                
                # Merge with existing call_result
                current_call_result = call_record.call_result.dict() if call_record.call_result else {}
                current_call_result.update(analysis_data)
                
                await call_record.update({"$set": {"call_result": current_call_result}})
                logger.success(f"✅ Analysis completed for call {call_record.id}")
                logger.info(f"📊 Analysis summary: {analysis_result.summary}")
                logger.info(f"📊 Quality score: {analysis_result.quality_score}")
                logger.info(f"📊 Customer intent: {analysis_result.customer_intent}")
                
            except Exception as e:
                logger.error(f"❌ Analysis failed for call {call_record.id}: {str(e)}")
                # Don't fail the webhook if analysis fails
        else:
            logger.info(f"⚠️ No transcript available for analysis in call {call_record.id}")

        return {
            "status": "success",
            "message": "Webhook processed successfully",
            "call_id": str(call_record.id),
            "call_sid": call_sid,
            "updated_status": mapped_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing custom assistant webhook: {e}")
        import traceback
        logger.error(f"📍 Full traceback: {traceback.format_exc()}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

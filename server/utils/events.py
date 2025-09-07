from typing import Dict, Any
from loguru import logger
from model.model import Call
from bson import ObjectId
from datetime import datetime
from utils.vapi_client import VAPIClient
from utils.analyst import analyze_transcript


async def handle_call_completion(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process call completion webhook data with transcript retrieval and Gemini analysis"""
    try:
        # Extract call info from nested structure
        message_data = webhook_data.get("message", {})
        call_info = webhook_data.get("call", {})

        # Try to get call ID from multiple possible locations
        vapi_call_id = (
            call_info.get("id")
            or message_data.get("call", {}).get("id")
            or webhook_data.get("call", {}).get("id")
        )

        if not vapi_call_id:
            logger.error("No call ID in webhook data")
            logger.error(f"Webhook structure: {webhook_data.keys()}")
            return {"status": "error", "message": "Missing call ID"}

        logger.info(f"🎯 Processing call completion for VAPI call: {vapi_call_id}")

        logger.info(f"🔍 Searching for call record with VAPI ID: {vapi_call_id}")
        call_record = await Call.find_one({"vapi_call_id": vapi_call_id})

        if not call_record:
            logger.error(f"❌ No call found with VAPI ID: {vapi_call_id}")
            return {"status": "error", "message": "Call not found"}

        logger.info(f"✅ Found call record: {call_record.id}")
        call_id = str(call_record.id)

        # Extract call details from webhook - check multiple locations
        status = (
            call_info.get("status", "unknown")
            or message_data.get("call", {}).get("status", "unknown")
            or "completed"  # Default for end-of-call-report
        ).lower()

        logger.info(f"📊 Extracted status: {status}")

        # Extract transcript from multiple possible locations
        webhook_transcript = (
            call_info.get("transcript", "")
            or message_data.get("transcript", "")
            or call_info.get("artifact", {}).get("transcript", "")
            or message_data.get("artifact", {}).get("transcript", "")
        )

        logger.info(f"📝 Webhook transcript length: {len(webhook_transcript)}")

        vapi_client = VAPIClient()
        # Process all calls (including end-of-call-report with unknown status)
        # For end-of-call-report events, we should process regardless of status
        should_process = status in ["completed", "ended"] or status == "unknown"

        if should_process:
            logger.info(f"✅ Processing call with status: {status}")

            # Step 1: Retrieve full transcript from VAPI API
            logger.info(
                f"📜 Retrieving full transcript from VAPI API for call: {vapi_call_id}"
            )

            try:
                full_transcript = await vapi_client.get_call_transcript(vapi_call_id)
                logger.info(f"📜 VAPI API transcript retrieval completed")
            except Exception as e:
                logger.error(f"❌ Error retrieving transcript from VAPI API: {e}")
                full_transcript = None
            # Use the more complete transcript (API vs webhook)
            final_transcript = (
                full_transcript
                if full_transcript and len(full_transcript) > len(webhook_transcript)
                else webhook_transcript
            )
            logger.info(f"📝 Final transcript length: {final_transcript}")
            if not final_transcript:
                logger.warning(f"⚠️ No transcript available for call {vapi_call_id}")
                final_transcript = "No transcript available"
            else:
                logger.info(
                    f"✅ Retrieved transcript with {len(final_transcript)} characters"
                )

            # Extract analysis data from webhook if available
            analysis_data = (
                message_data.get("analysis", {}) or call_info.get("analysis", {}) or {}
            )

            webhook_summary = analysis_data.get("summary", "")
            success_evaluation = analysis_data.get("successEvaluation", "")

            # Step 3: Analyze transcript with Gemini if available
            logger.info(f"📋 Analyzing transcript with Gemini for call: {vapi_call_id}")
            try:
                analyst_result = analyze_transcript(final_transcript)
                logger.info(f"📋 Analyst result: {analyst_result}")
            except Exception as e:
                logger.error(f"❌ Error analyzing transcript: {e}")
                # Create a default result if analysis fails
                from utils.analyst import AnalysisResult

                analyst_result = AnalysisResult(
                    summary="Analysis failed",
                    quality_score=0.0,
                    customer_intent="unknown",
                )

            # Use webhook analysis if available, otherwise use Gemini analysis
            final_summary = (
                webhook_summary if webhook_summary else analyst_result.summary
            )
            final_quality_score = analyst_result.quality_score
            final_customer_intent = analyst_result.customer_intent

            update_data = {
                "status": "completed",
                "call_result": {
                    "summary": final_summary,
                    "quality_score": final_quality_score,
                    "customer_intent": final_customer_intent,
                    "transcript": final_transcript,
                },
                "updated_at": datetime.utcnow(),
            }

            logger.info(f"💾 Updating call record with data: {update_data}")
            try:
                await call_record.update({"$set": update_data})
                logger.info(f"✅ Call result updated successfully: {call_id}")
                return {
                    "status": "success",
                    "message": "Call completion processed successfully",
                }
            except Exception as e:
                logger.error(f"❌ Error updating call record: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to update call record: {str(e)}",
                }
        else:
            logger.info(f"⚠️ Skipping call processing for status: {status}")
            return {
                "status": "skipped",
                "message": f"Call status '{status}' not processed",
            }
    except Exception as e:
        logger.error(f"❌ Error processing call completion: {e}")
        return {"status": "error", "message": str(e)}


async def handle_call_started(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process call started webhook data"""
    try:
        # Extract call info from nested structure
        message_data = webhook_data.get("message", {})
        call_info = webhook_data.get("call", {})

        # Try to get call ID from multiple possible locations
        vapi_call_id = (
            call_info.get("id")
            or message_data.get("call", {}).get("id")
            or webhook_data.get("call", {}).get("id")
        )

        if not vapi_call_id:
            logger.error("No call ID in webhook data")
            logger.error(f"Webhook structure: {webhook_data.keys()}")
            return {"status": "error", "message": "Missing call ID"}

        logger.info(f"📞 Call started: {vapi_call_id}")

        call_record = await Call.find_one({"vapi_call_id": vapi_call_id})

        if call_record:
            await call_record.update(
                {"$set": {"status": "in_progress", "updated_at": datetime.utcnow()}}
            )
            logger.info(f"✅ Updated call {vapi_call_id} to in_progress")
        else:
            logger.warning(f"⚠️ Call not found for VAPI ID: {vapi_call_id}")

        return {"status": "success", "vapi_call_id": vapi_call_id}

    except Exception as e:
        logger.error(f"Error handling call started: {e}")
        return {"status": "error", "message": str(e)}

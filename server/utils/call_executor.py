from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
import os

from model.model import CallStatus

# Add success level if it doesn't exist
if not hasattr(logger, "success"):
    logger.success = logger.info
import asyncio
import aiohttp

from model.vapi_model import VAPICallRequest, CallCustomer
from utils.vapi_client import VAPIClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get assistant ID from environment variables
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")


class CallExecutor:
    """Executes VAPI calls for scheduled interviews"""

    def __init__(self, vapi_client: VAPIClient):
        self.vapi_client = vapi_client

    async def execute_call(
        self, call_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute a VAPI call for the given call data using standardized assistants

        Returns:
            Tuple[success: bool, vapi_call_id: Optional[str], error_message: Optional[str]]
        """
        try:
            # Handle both dictionary and object inputs
            if hasattr(call_data, "id"):
                # It's a Beanie document object
                call_id = str(call_data.id)
                phone_number = call_data.user.phone
                name = call_data.user.name
            else:
                # It's a dictionary
                call_id = str(call_data.get("_id") or call_data.get("id", "unknown"))
                phone_number = call_data["user"]["phone"]
                name = call_data["user"]["name"]

            logger.info(f"🚀 [Call {call_id}] Starting call execution")
            logger.info(f"🚀 [Call {type(call_data)}] Starting call execution")

            logger.info(f"📞 [Call {call_id}] Target: {name} ({phone_number})")

            # Step 1: Get assistant ID from customer data
            logger.info(f"📋 [Call {call_id}] Step 1: Selecting assistant...")
            assistant_id = ASSISTANT_ID
            phone_number_id = PHONE_NUMBER_ID
            if not assistant_id:
                error_msg = "No assistant ID found for customer"
                logger.error(f"❌ [Call {call_id}] {error_msg}")
                return False, None, error_msg

            # Step 2: Prepare call request with assistant overrides

            logger.info(
                f"📝 [Call {call_id}] Step 2: Preparing call request with overrides..."
            )
            customer = CallCustomer(
                number=phone_number, name=name, numberE164CheckEnabled=True
            )
            assistant_overrides = {"variableValues": {"name": name}}
            call_request = VAPICallRequest(
                assistantId=assistant_id,
                phoneNumberId=phone_number_id,
                customer=customer,
                assistantOverrides=assistant_overrides,
            )

            logger.info(
                f"✅ [Call {call_id}] Call request prepared with assistant {assistant_id}"
            )

            # Step 3: Execute VAPI call
            logger.info(f"🎯 [Call {call_id}] Step 3: Executing VAPI call...")
            vapi_response = await self.vapi_client.initiate_call(call_request)

            if vapi_response and vapi_response.id:

                vapi_call_id = vapi_response.id
                logger.success(f"✅ [Call {call_id}] VAPI call created successfully!")
                logger.success(f"🎉 [Call {call_id}] VAPI Call ID: {vapi_call_id}")
                logger.info(f"📞 [Call {call_id}] Call initiated to {phone_number}")

                # Wait a moment to check initial call status
                logger.info(f"⏳ [Call {call_id}] Checking initial call status...")
                await asyncio.sleep(2)
                call_status = await self._check_call_status(vapi_call_id)

                if call_status:
                    logger.info(
                        f"📊 [Call {call_id}] Initial status: {call_status.get('status', 'unknown')}"
                    )
                    
                    call_data.vapi_call_id = vapi_call_id
                    call_data.status = CallStatus.INITIATED
                    await call_data.save()

                return True, vapi_call_id, None
                
            else:
                error_msg = f"VAPI call creation failed: {vapi_response}"
                logger.error(f"❌ [Call {call_id}] {error_msg}")
                return False, None, error_msg

        except Exception as e:
            error_msg = f"Call execution error: {str(e)}"
            logger.error(f"❌ [Call {call_id}] {error_msg}")
            import traceback

            logger.error(f"📊 [Call {call_id}] Stack trace: {traceback.format_exc()}")
            return False, None, error_msg


#     async def _get_customer_assistant_id(
#         self, call_data: Dict[str, Any]
#     ) -> Optional[str]:
#         """Get the appropriate assistant ID for the customer and language"""
#         try:
#             call_id = str(call_data.get("_id", "unknown"))
#             customer_id = call_data.get("customer_id", "unknown")

#             logger.info(
#                 f"🔍 [Call {call_id}] Starting assistant selection for customer: {customer_id}"
#             )

#             # Get language from job data (default to english)
#             language = call_data.get("job", {}).get("language", "english").lower()
#             logger.info(f"🌐 [Call {call_id}] Detected language: {language}")

#             # Get assistant IDs from customer data
#             vapi_assistants = call_data.get("vapi_assistants", {})
#             logger.info(f"📋 [Call {call_id}] Available assistants: {vapi_assistants}")

#             if language == "hindi":
#                 assistant_id = vapi_assistants.get("vapi_assistant_hi")
#                 if assistant_id:
#                     logger.success(
#                         f"✅ [Call {call_id}] Selected Hindi assistant: {assistant_id}"
#                     )
#                     return assistant_id
#                 else:
#                     logger.warning(
#                         f"⚠️ [Call {call_id}] No Hindi assistant found (vapi_assistant_hi missing), trying English"
#                     )
#                     # Fallback: try English if Hindi not present
#                     fallback_en = vapi_assistants.get("vapi_assistant_en")
#                     if fallback_en:
#                         logger.success(
#                             f"🔁 [Call {call_id}] Falling back to English assistant: {fallback_en}"
#                         )
#                         return fallback_en
#             else:
#                 # Default path prefers English
#                 assistant_id = vapi_assistants.get("vapi_assistant_en")
#                 if assistant_id:
#                     logger.success(
#                         f"✅ [Call {call_id}] Selected English assistant: {assistant_id}"
#                     )
#                     return assistant_id
#                 else:
#                     logger.warning(
#                         f"⚠️ [Call {call_id}] No English assistant found (vapi_assistant_en missing), trying Hindi"
#                     )
#                     # Fallback: try Hindi if English not present
#                     fallback_hi = vapi_assistants.get("vapi_assistant_hi")
#                     if fallback_hi:
#                         logger.success(
#                             f"🔁 [Call {call_id}] Falling back to Hindi assistant: {fallback_hi}"
#                         )
#                         return fallback_hi

#             logger.error(
#                 f"❌ [Call {call_id}] No assistant ID found for customer {customer_id}"
#             )
#             logger.error(
#                 f"❌ [Call {call_id}] Expected vapi_assistant_en or vapi_assistant_hi in customer data"
#             )
#             return None

#         except Exception as e:
#             logger.error(
#                 f"❌ [Call {call_id}] Error getting customer assistant ID: {e}"
#             )
#             return None

#     async def _prepare_call_request_with_overrides(
#         self,
#         assistant_id: str,
#         candidate_phone: str,
#         candidate_name: str,
#         call_data: Dict[str, Any],
#     ) -> "VAPICallRequest":
#         """Prepare the VAPI call request payload with assistant overrides"""

#         call_id = str(call_data.get("_id", "unknown"))

#         logger.info(f"🔧 [Call {call_id}] Building VAPI call request...")
#         logger.info(f"🤖 [Call {call_id}] Using assistant: {assistant_id}")
#         logger.info(f"📞 [Call {call_id}] Target phone: {candidate_phone}")
#         logger.info(f"👤 [Call {call_id}] Candidate: {candidate_name}")

#         # Ensure phone number is in E.164 format
#         if not candidate_phone.startswith("+"):
#             candidate_phone = f"+{candidate_phone}"
#             logger.info(
#                 f"📱 [Call {call_id}] Formatted phone to E.164: {candidate_phone}"
#             )

#         # Create customer object
#         customer = CallCustomer(
#             number=candidate_phone, name=candidate_name, numberE164CheckEnabled=True
#         )
#         logger.success(f"✅ [Call {call_id}] Customer object created")

#         # Prepare metadata
#         metadata = {
#             "call_id": str(call_data["_id"]),
#             "candidate_id": str(call_data["candidate_id"]),
#             "customer_id": call_data.get("customer_id", "unknown"),
#             "call_type": call_data.get("call_type", "screening"),
#             "retry_count": call_data.get("retry_count", 0),
#             "scheduled_time": call_data.get(
#                 "scheduled_time", datetime.utcnow()
#             ).isoformat(),
#         }
#         logger.success(f"✅ [Call {call_id}] Metadata prepared: {len(metadata)} fields")

#         # Get dynamic prompt for this call
#         logger.info(f"📝 [Call {call_id}] Getting assistant overrides...")
#         assistant_overrides = await self._get_assistant_overrides(call_data)

#         # Get phone number configuration
#         logger.info(f"📱 [Call {call_id}] Getting phone configuration...")
#         phone_config = await self._get_phone_configuration()

#         # Create the call request object
#         logger.info(f"🏗️ [Call {call_id}] Creating call request object...")

#         if phone_config and "phoneNumberId" in phone_config:
#             # Using VAPI phone number ID
#             logger.info(
#                 f"📞 [Call {call_id}] Using VAPI phone number ID: {phone_config['phoneNumberId']}"
#             )
#             call_request = VAPICallRequest(
#                 assistantId=assistant_id,
#                 phoneNumberId=phone_config["phoneNumberId"],
#                 customer=customer,
#                 maxDurationSeconds=600,
#                 metadata=metadata,
#                 assistantOverrides=assistant_overrides,
#             )
#             logger.success(
#                 f"✅ [Call {call_id}] VAPI call request created with phoneNumberId"
#             )

#         elif phone_config and "phoneNumber" in phone_config:
#             # Using Twilio phone number configuration
#             twilio_config = phone_config["phoneNumber"]
#             logger.info(
#                 f"📞 [Call {call_id}] Using Twilio config: {twilio_config.get('twilioPhoneNumber', 'unknown')}"
#             )

#             phone_number_obj = PhoneNumberObject(
#                 provider="twilio",
#                 twilioAccountSid=twilio_config["twilioAccountSid"],
#                 twilioAuthToken=twilio_config["twilioAuthToken"],
#                 twilioPhoneNumber=twilio_config["twilioPhoneNumber"],
#             )
#             call_request = VAPICallRequest(
#                 assistantId=assistant_id,
#                 phoneNumber=phone_number_obj,
#                 customer=customer,
#                 maxDurationSeconds=600,
#                 metadata=metadata,
#                 assistantOverrides=assistant_overrides,
#             )
#             logger.success(
#                 f"✅ [Call {call_id}] VAPI call request created with Twilio config"
#             )

#         else:
#             # Fallback - create minimal request (may fail if no phone config)
#             logger.warning(
#                 f"⚠️ [Call {call_id}] No phone config found, creating minimal request"
#             )
#             call_request = VAPICallRequest(
#                 assistantId=assistant_id,
#                 customer=customer,
#                 maxDurationSeconds=600,
#                 metadata=metadata,
#                 assistantOverrides=assistant_overrides,
#             )
#             logger.warning(
#                 f"⚠️ [Call {call_id}] Minimal call request created (may fail without phone config)"
#             )

#         # Log final request details
#         logger.success(f"✅ [Call {call_id}] Final call request prepared")
#         logger.info(f"📊 [Call {call_id}] Request summary:")
#         logger.info(f"   - Assistant ID: {assistant_id}")
#         logger.info(f"   - Customer: {candidate_name} ({candidate_phone})")
#         logger.info(f"   - Max Duration: 600 seconds")
#         logger.info(f"   - Metadata Fields: {len(metadata)}")
#         logger.info(
#             f"   - Assistant Overrides: {'✅' if assistant_overrides else '❌'}"
#         )

#         if assistant_overrides:
#             model_msgs = assistant_overrides.get("model", {}).get("messages", [])
#             first_msg = assistant_overrides.get("firstMessage", "")
#             logger.info(f"   - Override Messages: {len(model_msgs)}")
#             logger.info(f"   - First Message: {'✅' if first_msg else '❌'}")

#         # Log the actual JSON structure that will be sent to VAPI
#         try:
#             request_dict = call_request.model_dump(by_alias=True)
#             logger.info(f"🔍 [Call {call_id}] Final request JSON structure:")
#             logger.info(
#                 f"   - assistantId: {request_dict.get('assistantId', 'missing')}"
#             )
#             logger.info(
#                 f"   - phoneNumberId: {request_dict.get('phoneNumberId', 'missing')}"
#             )
#             logger.info(
#                 f"   - customer.number: {request_dict.get('customer', {}).get('number', 'missing')}"
#             )
#             logger.info(
#                 f"   - assistantOverrides: {'present' if request_dict.get('assistantOverrides') else 'MISSING!'}"
#             )

#             if request_dict.get("assistantOverrides"):
#                 overrides = request_dict["assistantOverrides"]
#                 logger.info(
#                     f"   - assistantOverrides.model.provider: {overrides.get('model', {}).get('provider', 'missing')}"
#                 )
#                 logger.info(
#                     f"   - assistantOverrides.model.model: {overrides.get('model', {}).get('model', 'missing')}"
#                 )
#                 logger.info(
#                     f"   - assistantOverrides.model.messages: {len(overrides.get('model', {}).get('messages', []))} messages"
#                 )
#                 logger.info(
#                     f"   - assistantOverrides.firstMessage: {'present' if overrides.get('firstMessage') else 'missing'}"
#                 )
#         except Exception as e:
#             logger.error(
#                 f"❌ [Call {call_id}] Error serializing request for logging: {e}"
#             )

#         return call_request

#     async def _get_assistant_overrides(
#         self, call_data: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """Generate assistant overrides with dynamic prompt"""
#         try:
#             call_id = str(call_data.get("_id", "unknown"))
#             customer_id = call_data.get("customer_id")

#             logger.info(
#                 f"📝 [Call {call_id}] Starting prompt generation for customer: {customer_id}"
#             )

#             # Get prompt from database using prompt service
#             from services.prompt_service import PromptService

#             # Extract job and company information
#             job_info = call_data.get("job", {})
#             company_info = call_data.get("company", {})

#             # Get language from job data
#             language = job_info.get("language", "english").lower()

#             logger.info(
#                 f"🏢 [Call {call_id}] Company: {company_info.get('company_name', 'Unknown')}"
#             )
#             logger.info(
#                 f"💼 [Call {call_id}] Job: {job_info.get('job_title', 'Unknown')}"
#             )
#             logger.info(f"🌐 [Call {call_id}] Language: {language}")
#             logger.info(
#                 f"📊 [Call {call_id}] Experience Level: {job_info.get('experience_level', 'any')}"
#             )
#             logger.info(
#                 f"📋 [Call {call_id}] Questions: {len(job_info.get('questions', []))} provided"
#             )

#             # Create job context
#             job_context_dict = {
#                 "company_name": company_info.get("company_name", "Company"),
#                 "job_title": job_info.get("job_title", "Position"),
#                 "description": job_info.get("job_description", ""),
#                 "experience_level": job_info.get("experience_level", "any"),
#                 "requirements": job_info.get("requirements", []),
#                 "questions": job_info.get("questions", []),
#             }

#             # Create candidate context
#             candidate_context_dict = {
#                 "candidate_name": call_data.get("candidate_name", "Candidate"),
#                 "relevant_skills": [],
#                 "experience_years": None,
#                 "resume_summary": None,
#             }

#             logger.info(
#                 f"👤 [Call {call_id}] Candidate: {candidate_context_dict['candidate_name']}"
#             )

#             # Get dynamic prompts from database with language support
#             logger.info(
#                 f"🔍 [Call {call_id}] Retrieving system prompt from database (language: {language})..."
#             )
#             system_prompt = await PromptService.get_vapi_interview_prompt(
#                 job_context_dict, candidate_context_dict, customer_id, language
#             )

#             logger.info(
#                 f"🔍 [Call {call_id}] Retrieving first message from database (language: {language})..."
#             )
#             first_message = await PromptService.get_vapi_first_message(
#                 job_context_dict, candidate_context_dict, customer_id, language
#             )

#             # Log prompt details
#             prompt_length = len(system_prompt)
#             first_msg_length = len(first_message)

#             logger.success(
#                 f"✅ [Call {call_id}] System prompt retrieved ({language}): {prompt_length} characters"
#             )
#             logger.success(
#                 f"✅ [Call {call_id}] First message retrieved ({language}): {first_msg_length} characters"
#             )

#             # Show preview of prompts
#             logger.info(
#                 f"📖 [Call {call_id}] System prompt preview: {system_prompt[:150]}..."
#             )
#             logger.info(
#                 f"📖 [Call {call_id}] First message preview: {first_message[:100]}..."
#             )

#             # Create assistant overrides that match VAPI's expected structure
#             overrides = {
#                 "model": {
#                     "provider": "openai",
#                     "model": "gpt-4o-mini",
#                     "messages": [{"role": "system", "content": system_prompt}],
#                 },
#                 "firstMessage": first_message,
#             }

#             logger.success(
#                 f"✅ [Call {call_id}] Assistant overrides generated successfully"
#             )
#             logger.info(
#                 f"📊 [Call {call_id}] Override structure: model.messages[0], firstMessage"
#             )

#             # Log the exact structure for debugging
#             logger.info(f"🔍 [Call {call_id}] Assistant Override Structure:")
#             logger.info(f"   - Provider: {overrides['model']['provider']}")
#             logger.info(f"   - Model: {overrides['model']['model']}")
#             logger.info(f"   - Messages: {len(overrides['model']['messages'])}")
#             logger.info(
#                 f"   - First Message: {'present' if overrides.get('firstMessage') else 'missing'}"
#             )

#             return overrides

#         except Exception as e:
#             logger.error(
#                 f"❌ [Call {call_id}] Error generating assistant overrides: {e}"
#             )
#             logger.warning(f"⚠️ [Call {call_id}] Using fallback prompt")

#             # Get language for fallback (default to english if not available)
#             language = "english"
#             try:
#                 job_info = call_data.get("job", {})
#                 language = job_info.get("language", "english").lower()
#             except Exception:
#                 pass

#             # Create language-appropriate fallback
#             if language == "hindi":
#                 fallback_content = (
#                     "आप एक सहायक साक्षात्कार सहायक हैं। एक पेशेवर साक्षात्कार आयोजित करें।"
#                 )
#                 fallback_first_message = "नमस्कार! साक्षात्कार के लिए धन्यवाद।"
#             else:
#                 fallback_content = "You are a helpful interview assistant. Conduct a professional interview."
#                 fallback_first_message = "Hello! Thank you for taking the interview."

#             fallback_overrides = {
#                 "model": {
#                     "provider": "openai",
#                     "model": "gpt-4o-mini",
#                     "messages": [{"role": "system", "content": fallback_content}],
#                 },
#                 "firstMessage": fallback_first_message,
#             }

#             logger.info(
#                 f"🔄 [Call {call_id}] Fallback override created (language: {language})"
#             )
#             return fallback_overrides

#     async def _get_phone_configuration(self) -> Optional[Dict[str, Any]]:
#         """Get phone number configuration for VAPI calls"""
#         try:
#             from config.settings import settings

#             # Try VAPI phone number first
#             if (
#                 hasattr(settings, "vapi_phone_number_id")
#                 and settings.vapi_phone_number_id
#             ):
#                 return {"phoneNumberId": settings.vapi_phone_number_id}

#             # Fallback to Twilio configuration
#             if (
#                 hasattr(settings, "twilio_account_sid")
#                 and hasattr(settings, "twilio_auth_token")
#                 and hasattr(settings, "twilio_phone_number")
#                 and settings.twilio_account_sid
#                 and settings.twilio_auth_token
#                 and settings.twilio_phone_number
#             ):

#                 return {
#                     "phoneNumber": {
#                         "twilioAccountSid": settings.twilio_account_sid,
#                         "twilioAuthToken": settings.twilio_auth_token,
#                         "twilioPhoneNumber": settings.twilio_phone_number,
#                     }
#                 }

#             logger.warning("⚠️ No phone configuration found")
#             return None

#         except Exception as e:
#             logger.error(f"Error getting phone configuration: {e}")
#             return None

    async def _check_call_status(self, vapi_call_id: str) -> Optional[Dict[str, Any]]:
        """Check the status of a VAPI call"""
        try:
            # Get call details from VAPI
            call_details = await self.vapi_client.get_call(vapi_call_id)

            if call_details:
                status = call_details.get("status", "unknown")
                logger.info(f"📞 Call {vapi_call_id} status: {status}")
                return call_details

            return None

        except Exception as e:
            logger.error(f"Error checking call status: {e}")
            return None

#     def _get_default_system_prompt(self) -> str:
#         """Get default system prompt for interview assistant"""
#         return """You are a professional AI interviewer conducting a brief screening call for a job application.

# Your goals:
# 1. Confirm the candidate's interest in the position
# 2. Ask 2-3 relevant screening questions about their background
# 3. Assess their communication skills and enthusiasm
# 4. Keep the call professional but friendly
# 5. Limit the call to 5-10 minutes

# Guidelines:
# - Be polite and professional
# - Listen actively to their responses
# - Ask follow-up questions if needed
# - Thank them for their time
# - Let them know next steps will be communicated soon

# Start by confirming their availability and proceed with the screening questions."""


# class CallStatusChecker:
#     """Monitors and updates call statuses"""

#     def __init__(self, vapi_client: VAPIClient):
#         self.vapi_client = vapi_client

#     async def check_and_update_call_status(
#         self, vapi_call_id: str, call_manager, call_id: str
#     ) -> bool:
#         """Check VAPI call status and update database accordingly"""
#         try:
#             call_details = await self.vapi_client.get_call(vapi_call_id)

#             if not call_details:
#                 logger.warning(f"⚠️ Could not retrieve call details for {vapi_call_id}")
#                 return False

#             status = call_details.get("status", "unknown").lower()
#             duration = call_details.get("duration", 0)
#             ended_reason = call_details.get("endedReason", "").lower()

#             logger.info(
#                 f"📞 Call {vapi_call_id} status: {status}, duration: {duration}s, endedReason: {ended_reason}"
#             )

#             # Check for voicemail first - this should be treated as failed
#             if ended_reason == "voicemail":
#                 logger.warning(
#                     f"⚠️ Call {vapi_call_id} went to voicemail - marking as failed for retry"
#                 )
#                 # Don't save duration, transcript, or any completion data
#                 # Just mark as failed so it can be retried
#                 await call_manager.update_call_status(
#                     call_id=call_id,
#                     status="failed",
#                     error_message="Call went to voicemail - will retry",
#                 )
#                 return False

#             # Map VAPI status to our status
#             if status in ["completed", "ended"]:
#                 # Only mark as completed if it didn't go to voicemail
#                 if ended_reason and ended_reason != "voicemail":
#                     # Call completed successfully
#                     await call_manager.update_call_status(
#                         call_id=call_id, status="completed", call_duration=duration
#                     )
#                     return True
#                 else:
#                     # Call ended but went to voicemail - mark as failed
#                     logger.warning(
#                         f"⚠️ Call {vapi_call_id} ended but went to voicemail - marking as failed"
#                     )
#                     await call_manager.update_call_status(
#                         call_id=call_id,
#                         status="failed",
#                         error_message="Call ended but went to voicemail - will retry",
#                     )
#                     return False

#             elif status in ["failed", "busy", "no-answer", "cancelled"]:
#                 # Call failed - needs retry
#                 logger.warning(f"⚠️ Call {vapi_call_id} failed with status: {status}")
#                 return False

#             elif status in ["ringing", "in-progress", "connecting"]:
#                 # Call still active
#                 await call_manager.update_call_status(
#                     call_id=call_id, status="in_progress"
#                 )
#                 return True

#             else:
#                 logger.warning(f"⚠️ Unknown call status: {status}")
#                 return False

#         except Exception as e:
#             logger.error(f"Error checking call status: {e}")
#             return False

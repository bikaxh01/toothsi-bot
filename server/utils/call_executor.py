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
# ASSISTANT_ID = os.getenv("ASSISTANT_ID")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")


class CallExecutor:
    """Executes VAPI calls for scheduled interviews"""

    def __init__(self, vapi_client: VAPIClient):
        self.vapi_client = vapi_client

    async def execute_call(
        self, call_data: Dict[str, Any], assistant_id: str
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

    async def execute_custom_call(
        self, call_data: Dict[str, Any], custom_url: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute a custom API call for the given call data using external API

        Returns:
            Tuple[success: bool, custom_call_id: Optional[str], error_message: Optional[str]]
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

            logger.info(f"🚀 [Custom Call {call_id}] Starting custom call execution")
            logger.info(f"📞 [Custom Call {call_id}] Target: {name} ({phone_number})")
            logger.info(f"🌐 [Custom Call {call_id}] Custom URL: {custom_url}")

            # Prepare payload for custom API
            payload = {
                "name": name,
                "phone": phone_number,
            }

            logger.info(f"📤 [Custom Call {call_id}] Sending payload: {payload}")

            # Make API call to custom endpoint
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    custom_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        # Extract custom call details from response
                        call_sid = response_data.get("call_sid")
                        call_status = response_data.get("status")
                        phone_number = response_data.get("phone_number")
                        customer_name = response_data.get("customer_name")
                        
                        # Validate required fields
                        if not call_sid:
                            error_msg = "Missing call_sid in custom API response"
                            logger.error(f"❌ [Custom Call {call_id}] {error_msg}")
                            return False, None, error_msg
                        
                        logger.success(f"✅ [Custom Call {call_id}] Custom API call successful!")
                        logger.success(f"🎉 [Custom Call {call_id}] Call SID: {call_sid}")
                        logger.info(f"📞 [Custom Call {call_id}] Status: {call_status}")
                        logger.info(f"📞 [Custom Call {call_id}] Phone: {phone_number}")
                        logger.info(f"📞 [Custom Call {call_id}] Customer: {customer_name}")
                        logger.info(f"📞 [Custom Call {call_id}] Full Response: {response_data}")

                        # Update call data with custom call details
                        if hasattr(call_data, "vapi_call_id"):
                            call_data.vapi_call_id = call_sid
                            # Map custom status to CallStatus enum
                            if call_status == "call_initiated":
                                call_data.status = CallStatus.INITIATED
                            else:
                                call_data.status = CallStatus.INITIATED  # Default fallback
                            await call_data.save()

                        return True, call_sid, None
                    else:
                        error_msg = f"Custom API call failed with status {response.status}: {response_data}"
                        logger.error(f"❌ [Custom Call {call_id}] {error_msg}")
                        return False, None, error_msg

        except asyncio.TimeoutError:
            error_msg = "Custom API call timed out"
            logger.error(f"❌ [Custom Call {call_id}] {error_msg}")
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Custom call execution error: {str(e)}"
            logger.error(f"❌ [Custom Call {call_id}] {error_msg}")
            import traceback
            logger.error(f"📊 [Custom Call {call_id}] Stack trace: {traceback.format_exc()}")
            return False, None, error_msg

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




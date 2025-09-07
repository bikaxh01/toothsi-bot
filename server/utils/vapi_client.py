import httpx
import json
import os
from typing import Dict, Any, Optional, List
from loguru import logger
from dotenv import load_dotenv
from model.vapi_model import VAPICallRequest, VAPICallResponse

# Load environment variables
load_dotenv()
from model.vapi_model import VAPICallRequest, VAPICallResponse


class VAPIClient:
    """VAPI API Client for managing assistants and calls"""

    def __init__(self):
        self.base_url = os.getenv("VAPI_BASE_URL", "https://api.vapi.ai")
        self.api_key = os.getenv("VAPI_API_KEY")

        if not self.api_key:
            raise ValueError("VAPI_API_KEY environment variable is not set")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # async def test_connection(self) -> bool:
    #     """Test VAPI API connectivity"""
    #     try:
    #         async with httpx.AsyncClient() as client:
    #             response = await client.get(
    #                 f"{self.base_url}/assistant", headers=self.headers, timeout=10.0
    #             )
    #             success = response.status_code == 200
    #             logger.info(
    #                 f"VAPI connection test: {'SUCCESS' if success else 'FAILED'} (Status: {response.status_code})"
    #             )
    #             return success
    #     except Exception as e:
    #         logger.error(f"VAPI connection test failed: {e}")
    #         return False

    async def initiate_call(
        self, call_data: VAPICallRequest
    ) -> Optional[VAPICallResponse]:
        """Initiate a call using VAPI"""
        try:
            async with httpx.AsyncClient() as client:
                logger.info(f"Initiating call: {call_data.model_dump(exclude_none=True)} 🟢🟢")
                response = await client.post(
                    f"{self.base_url}/call",
                    headers=self.headers,
                    json=call_data.model_dump(exclude_none=True),
                    timeout=30.0,
                )

                if response.status_code == 201:
                    data = response.json()
                    logger.info(f"Call initiated successfully: {data.get('id')}")

                    return VAPICallResponse(**data)
                else:
                    logger.error(
                        f"Failed to initiate call: {response.status_code} - {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error initiating call: {e}")
            return None

    async def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get call details by ID"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/call/{call_id}",
                    headers=self.headers,
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Retrieved call: {call_id}")
                    return data
                else:
                    logger.error(
                        f"Failed to get call {call_id}: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error getting call {call_id}: {e}")
            return None

    async def get_call_transcript(self, call_id: str) -> Optional[str]:
        """Get call transcript by ID - transcript is included in call details"""
        try:
            # Get full call details which should include transcript
            call_data = await self.get_call(call_id)

            if call_data:
                # Extract transcript from call data
                transcript = call_data.get("transcript", "")
                if transcript:
                    logger.info(
                        f"✅ Retrieved transcript for call {call_id}: {len(transcript)} chars"
                    )
                    return transcript
                else:
                    logger.warning(f"⚠️ No transcript found in call data for {call_id}")
                    return None
            else:
                logger.error(f"❌ Could not retrieve call data for {call_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting transcript for call {call_id}: {e}")
            return None

    # async def get_call_recording(self, call_id: str) -> Optional[str]:
    #     """Get call recording URL by ID"""
    #     try:
    #         async with httpx.AsyncClient() as client:
    #             response = await client.get(
    #                 f"{self.base_url}/call/{call_id}/recording",
    #                 headers=self.headers,
    #                 timeout=10.0,
    #             )

    #             if response.status_code == 200:
    #                 data = response.json()
    #                 recording_url = data.get("recordingUrl", "")
    #                 logger.info(f"Retrieved recording URL for call: {call_id}")
    #                 return recording_url
    #             else:
    #                 logger.error(
    #                     f"Failed to get recording for call {call_id}: {response.status_code}"
    #                 )
    #                 return None

    #     except Exception as e:
    #         logger.error(f"Error getting recording for call {call_id}: {e}")
    #         return None

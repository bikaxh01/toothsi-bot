from pydantic import BaseModel
from typing import Optional, Dict, Any, List



class CallCustomer(BaseModel):
    """Customer/destination configuration for VAPI call"""
    number: str  # Phone number in E.164 format (e.g., "+919073554610") 
    numberE164CheckEnabled: Optional[bool] = True
    name: Optional[str] = None  # Customer name
    extension: Optional[str] = None  # Phone extension if needed
    sipUri: Optional[str] = None  # SIP URI for SIP calls


class VAPICallRequest(BaseModel):
    """Request model for initiating VAPI call"""
  
    assistantId: str = None
    phoneNumberId: str = None

    customer: CallCustomer 
    maxDurationSeconds: Optional[int] = 600  # 10 minutes default
    # Assistant overrides for dynamic prompts (camelCase for VAPI API)
    assistantOverrides: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class VAPICallResponse(BaseModel):
    """Response model for VAPI call initiation"""
    id: str
    status: str
    createdAt: str
    updatedAt: str
    customer: Optional[CallCustomer] = None
    assistantId: Optional[str] = None
    phoneNumberId: Optional[str] = None
    maxDurationSeconds: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

#!/usr/bin/env python3
"""
Test script for VAPI tool call handler
This script demonstrates how the tool call handler processes VAPI tool call requests
"""

import asyncio
import json
from utils.tools import handle_tool_call

# Sample VAPI tool call request (based on your example)
SAMPLE_VECTOR_SEARCH_REQUEST = {
    "message": {
        "timestamp": 1678901234567,
        "type": "tool-calls",
        "toolCallList": [
            {
                "id": "toolu_01DTPAzUm5Gk3zxrpJ969oMF",
                "name": "vector_search",
                "arguments": {
                    "query": "privacy policy"
                }
            }
        ],
        "toolWithToolCallList": [
            {
                "type": "function",
                "name": "vector_search",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string"
                        }
                    }
                },
                "description": "Searches the knowledge base using vector similarity",
                "server": {
                    "url": "https://your-server.com/vapi/tools"
                },
                "messages": [],
                "toolCall": {
                    "id": "toolu_01DTPAzUm5Gk3zxrpJ969oMF",
                    "type": "function",
                    "function": {
                        "name": "vector_search",
                        "parameters": {
                            "query": "privacy policy"
                        }
                    }
                }
            }
        ],
        "artifact": {
            "messages": []
        },
        "assistant": {
            "name": "Knowledge Assistant",
            "description": "An assistant that provides information from knowledge base",
            "model": {},
            "voice": {},
            "artifactPlans": {},
            "startSpeakingPlan": {}
        },
        "call": {
            "id": "call-uuid",
            "orgId": "org-uuid",
            "type": "webCall",
            "assistant": {}
        }
    }
}

SAMPLE_PINCODE_REQUEST = {
    "message": {
        "timestamp": 1678901234567,
        "type": "tool-calls",
        "toolCallList": [
            {
                "id": "toolu_01DTPAzUm5Gk3zxrpJ969oMF",
                "name": "get_pincode_data",
                "arguments": {
                    "pincode": "110001",
                    "city": "New Delhi"
                }
            }
        ],
        "toolWithToolCallList": [
            {
                "type": "function",
                "name": "get_pincode_data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pincode": {
                            "type": "string"
                        },
                        "city": {
                            "type": "string"
                        }
                    }
                },
                "description": "Retrieves pincode data including clinic information",
                "server": {
                    "url": "https://your-server.com/vapi/tools"
                },
                "messages": [],
                "toolCall": {
                    "id": "toolu_01DTPAzUm5Gk3zxrpJ969oMF",
                    "type": "function",
                    "function": {
                        "name": "get_pincode_data",
                        "parameters": {
                            "pincode": "110001",
                            "city": "New Delhi"
                        }
                    }
                }
            }
        ],
        "artifact": {
            "messages": []
        },
        "assistant": {
            "name": "Pincode Assistant",
            "description": "An assistant that provides pincode and clinic information",
            "model": {},
            "voice": {},
            "artifactPlans": {},
            "startSpeakingPlan": {}
        },
        "call": {
            "id": "call-uuid",
            "orgId": "org-uuid",
            "type": "webCall",
            "assistant": {}
        }
    }
}


async def test_vector_search():
    """Test vector search tool call"""
    print("🔍 Testing Vector Search Tool Call")
    print("=" * 50)
    
    # Extract the tool call data from the request
    tool_call_data = SAMPLE_VECTOR_SEARCH_REQUEST["message"]["toolWithToolCallList"][0]
    
    try:
        result = await handle_tool_call(tool_call_data)
        print(f"✅ Vector Search Result:")
        print(f"Tool Call ID: {result.get('toolCallId')}")
        print(f"Result: {result.get('result')}")
    except Exception as e:
        print(f"❌ Vector Search Error: {e}")


async def test_pincode_data():
    """Test pincode data tool call"""
    print("\n📍 Testing Pincode Data Tool Call")
    print("=" * 50)
    
    # Extract the tool call data from the request
    tool_call_data = SAMPLE_PINCODE_REQUEST["message"]["toolWithToolCallList"][0]
    
    try:
        result = await handle_tool_call(tool_call_data)
        print(f"✅ Pincode Data Result:")
        print(f"Tool Call ID: {result.get('toolCallId')}")
        print(f"Result: {result.get('result')}")
    except Exception as e:
        print(f"❌ Pincode Data Error: {e}")


async def test_unknown_tool():
    """Test unknown tool call"""
    print("\n❓ Testing Unknown Tool Call")
    print("=" * 50)
    
    # Create a request with an unknown tool
    unknown_tool_data = {
        "toolCall": {
            "id": "toolu_unknown",
            "type": "function",
            "function": {
                "name": "unknown_tool",
                "parameters": {
                    "param1": "value1"
                }
            }
        }
    }
    
    try:
        result = await handle_tool_call(unknown_tool_data)
        print(f"✅ Unknown Tool Result:")
        print(f"Tool Call ID: {result.get('toolCallId')}")
        print(f"Result: {result.get('result')}")
    except Exception as e:
        print(f"❌ Unknown Tool Error: {e}")


async def main():
    """Run all tests"""
    print("🚀 VAPI Tool Call Handler Test Suite")
    print("=" * 60)
    
    await test_vector_search()
    await test_pincode_data()
    await test_unknown_tool()
    
    print("\n🎉 Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())

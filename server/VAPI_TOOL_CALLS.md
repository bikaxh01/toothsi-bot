# VAPI Tool Call Handler

This document explains how the VAPI tool call handler works and how to use it with your VAPI assistant.

## Overview

The tool call handler processes tool calls from VAPI assistants and routes them to the appropriate functions. It supports two main tools:

1. **vector_search** - Searches the knowledge base using vector similarity
2. **get_pincode_data** - Retrieves pincode and clinic information

## Request Format

VAPI sends tool call requests in the following format:

```json
{
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
```

## Available Tools

### 1. Vector Search Tool

**Tool Name:** `vector_search`

**Description:** Searches the knowledge base using vector similarity to find relevant content.

**Parameters:**
- `query` (string, required): The search query

**Example Request:**
```json
{
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
```

**Example Response:**
```json
{
    "toolCallId": "toolu_01DTPAzUm5Gk3zxrpJ969oMF",
    "result": "Found 1 result(s) for 'privacy policy':\n\n1. Our privacy policy outlines how we collect and use your data...\n(Relevance: 0.95)"
}
```

### 2. Pincode Data Tool

**Tool Name:** `get_pincode_data`

**Description:** Retrieves pincode data including clinic information and home scan availability.

**Parameters:**
- `pincode` (string, optional): The pincode to search for
- `city` (string, optional): The city to search for

**Example Request:**
```json
{
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
```

**Example Response:**
```json
{
    "toolCallId": "toolu_01DTPAzUm5Gk3zxrpJ969oMF",
    "result": "Found 1 pincode record(s):\n\n1. Pincode: 110001\n   City: New Delhi\n   Home Scan: Yes\n   Clinic 1: Toothsi Clinic Connaught Place\n   Clinic 2: Toothsi Clinic CP"
}
```

## API Endpoint

The tool call handler is available at:

```
POST /vapi/tools
```

**Request Body:** The full VAPI tool call request as shown above.

**Response Format:**
```json
{
    "results": [
        {
            "toolCallId": "toolu_01DTPAzUm5Gk3zxrpJ969oMF",
            "result": "Tool-specific result as a string"
        }
    ]
}
```

## Error Handling

The handler includes comprehensive error handling:

1. **Unknown Tool:** Returns an error with available tools list
2. **Missing Parameters:** Returns specific error messages
3. **Tool Execution Errors:** Returns detailed error information
4. **Malformed Requests:** Returns parsing errors

**Error Response Format:**
```json
{
    "toolCallId": "toolu_01DTPAzUm5Gk3zxrpJ969oMF",
    "result": "Error: Query parameter is required for vector search"
}
```

## Testing

Use the provided test script to verify the tool call handler:

```bash
python test_tool_calls.py
```

This will test:
- Vector search functionality
- Pincode data retrieval
- Unknown tool handling
- Error scenarios

## VAPI Assistant Configuration

To use these tools with your VAPI assistant, configure them in your assistant settings:

### Vector Search Tool Configuration
```json
{
    "type": "function",
    "name": "vector_search",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query for the knowledge base"
            }
        },
        "required": ["query"]
    },
    "description": "Searches the knowledge base using vector similarity to find relevant content",
    "server": {
        "url": "https://your-server.com/vapi/tools"
    }
}
```

### Pincode Data Tool Configuration
```json
{
    "type": "function",
    "name": "get_pincode_data",
    "parameters": {
        "type": "object",
        "properties": {
            "pincode": {
                "type": "string",
                "description": "The pincode to search for"
            },
            "city": {
                "type": "string",
                "description": "The city to search for"
            }
        }
    },
    "description": "Retrieves pincode data including clinic information and home scan availability",
    "server": {
        "url": "https://your-server.com/vapi/tools"
    }
}
```

## Implementation Details

### File Structure
- `utils/tools.py` - Contains the tool call handler and individual tool functions
- `main.py` - Contains the `/vapi/tools` endpoint
- `test_tool_calls.py` - Test script for the tool call handler

### Key Functions
- `handle_tool_call()` - Main handler that routes tool calls
- `handle_vector_search_tool()` - Processes vector search requests
- `handle_get_pincode_data_tool()` - Processes pincode data requests

### Dependencies
- FastAPI for the web endpoint
- Loguru for logging
- MongoDB for data storage
- OpenAI embeddings for vector search

## Security Considerations

1. **Input Validation:** All parameters are validated before processing
2. **Error Handling:** Sensitive information is not exposed in error messages
3. **Rate Limiting:** Consider implementing rate limiting for production use
4. **Authentication:** Add authentication if needed for production deployment

## Monitoring and Logging

The handler includes comprehensive logging:
- Tool call initiation and completion
- Parameter validation
- Error tracking
- Performance metrics

All logs use structured logging with the Loguru library for easy monitoring and debugging.

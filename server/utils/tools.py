

import pandas as pd
from typing import Dict, List, Optional, Any
from loguru import logger
from model.model import PincodeData
from utils.analyst import vector_search

async def extract_pincode_data() -> List[Dict]:
    """
    Extract pincode data from both Excel files and return a single list.
    Returns a list of dictionaries with keys: pincode, home_scan, clinic_1, clinic_2, city
    """
    try:
        # Read both Excel files
        df1 = pd.read_excel('pincode_data(1).xlsx')
        df2 = pd.read_excel('pincode_data(2).xlsx')
        
        logger.info(f"Successfully read pincode_data(1).xlsx with {len(df1)} rows")
        logger.info(f"Successfully read pincode_data(2).xlsx with {len(df2)} rows")
        
        # Initialize result list
        result = []
        
        # Process first file
        for index, row in df1.iterrows():
            pincode = str(row['pincode']).strip() if pd.notna(row['pincode']) else ""
            home_scan = str(row['home_scan_available']).strip() if pd.notna(row['home_scan_available']) else ""
            clinic_1 = str(row['clinic_1']).strip() if pd.notna(row['clinic_1']) else ""
            clinic_2 = str(row['clinic_2']).strip() if pd.notna(row['clinic_2']) else ""
            city = ""  # First file doesn't have city column
            
            # Skip if pincode is empty
            if not pincode:
                continue
            
            # Only add if at least one clinic exists
            if clinic_1 or clinic_2:
                result.append({
                    "pincode": pincode,
                    "home_scan": home_scan,
                    "clinic_1": clinic_1 if clinic_1 else "",
                    "clinic_2": clinic_2 if clinic_2 else "",
                    "city": city
                })
        
        # Process second file
        for index, row in df2.iterrows():
            pincode = str(row['pincode']).strip() if pd.notna(row['pincode']) else ""
            home_scan = str(row['home_scan_available']).strip() if pd.notna(row['home_scan_available']) else ""
            clinic_1 = str(row['nearby clinic_1_display_name']).strip() if pd.notna(row['nearby clinic_1_display_name']) else ""
            clinic_2 = str(row['nearby clinic_2_display_name']).strip() if pd.notna(row['nearby clinic_2_display_name']) else ""
            city = str(row['city']).strip() if pd.notna(row['city']) else ""
            
            # Skip if pincode is empty
            if not pincode:
                continue
            
            # Only add if at least one clinic exists
            if clinic_1 or clinic_2:
                
                result.append({
                    "pincode": pincode,
                    "home_scan": home_scan,
                    "clinic_1": clinic_1 if clinic_1 else "",
                    "clinic_2": clinic_2 if clinic_2 else "",
                    "city": city
                })
        
        logger.info(f"Extracted {len(result)} total pincode entries")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing pincode data: {e}")
        raise e
    
    
async def save_pincode_data() -> List[PincodeData]:
    """
    Save pincode data to the database
    """
    pincode_data_dicts = await extract_pincode_data()
    logger.info(f"Saving {len(pincode_data_dicts)} pincode data to the database")
    
    # Convert dictionaries to PincodeData document instances
    pincode_documents = []
    for data in pincode_data_dicts:
        pincode_doc = PincodeData(
            pincode=data["pincode"],
            home_scan=data["home_scan"],
            clinic_1=data["clinic_1"] if data["clinic_1"] else None,
            clinic_2=data["clinic_2"] if data["clinic_2"] else None,
            city=data["city"]
        )
        pincode_documents.append(pincode_doc)
    
    # Insert all documents
    await PincodeData.insert_many(pincode_documents)
    logger.info(f"Saved {len(pincode_documents)} pincode data to the database")
    
    # Return all pincode data from database
    pincode_data = await PincodeData.find().to_list()
    logger.info(f"Found {len(pincode_data)} pincode data in the database")
    return pincode_data




async def get_pincode_data(pincode: Optional[str] = None, city: Optional[str] = None) -> List[PincodeData]:
    """
    Get pincode data from the database based on pincode and/or city filters
    """
    # Build query filter
    query_filter = {}
    if pincode:
        query_filter["pincode"] = pincode
    if city:
        query_filter["city"] = city
    
    # Execute query
    pincode_data = await PincodeData.find(query_filter).limit(10).to_list()
    logger.info(f"Found {len(pincode_data)} pincode data in the database")
    
    if not pincode_data:
        logger.warning(f"No pincode data found in the database for pincode: {pincode} and city: {city}")
    
    # Convert list of PincodeData objects to JSON
    json_data = []
    for data in pincode_data:
        json_data.append(data.model_dump())
    
    return str(json_data)


async def handle_tool_call(tool_call_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle VAPI tool call requests
    
    Args:
        tool_call_data: The tool call data from VAPI
        
    Returns:
        Dict containing the tool call result in VAPI format
    """
    try:
        # Extract tool call information
        tool_call = tool_call_data.get("toolCall", {})
        tool_name = tool_call.get("function", {}).get("name", "")
        tool_parameters = tool_call.get("function", {}).get("parameters", {})
        tool_call_id = tool_call.get("id", "")
        
        logger.info(f"🔧 Processing tool call: {tool_name} with ID: {tool_call_id}")
        logger.info(f"📋 Tool parameters: {tool_parameters}")
        
        # Route to appropriate tool function
        if tool_name == "vector_search":
            result_string = await handle_vector_search_tool(tool_parameters)
        elif tool_name == "get_pincode_data":
            result_string = await handle_get_pincode_data_tool(tool_parameters)
        else:
            logger.warning(f"⚠️ Unknown tool: {tool_name}")
            result_string = f"Error: Unknown tool '{tool_name}'. Available tools: vector_search, get_pincode_data"
        
        return {
            "toolCallId": tool_call_id,
            "result": result_string
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling tool call: {e}")
        return {
            "toolCallId": tool_call_data.get("toolCall", {}).get("id", ""),
            "result": f"Error: {str(e)}"
        }


async def handle_vector_search_tool(parameters: Dict[str, Any]) -> str:
    """
    Handle vector search tool calls
    
    Args:
        parameters: Tool parameters containing 'query'
        
    Returns:
        String containing search results
    """
    try:
        query = parameters.get("query", "")
        if not query:
            return "Error: Query parameter is required for vector search"
        
        logger.info(f"🔍 Performing vector search for query: {query}")
        
        # Perform vector search
        search_results = await vector_search(query)
        
        if not search_results:
            return f"No results found for query: '{query}'"
        
        # Format results as a readable string
        result_text = f"Found {len(search_results)} result(s) for '{query}':\n\n"
        
        for i, result in enumerate(search_results, 1):
            content = result.get("content", "")
            score = result.get("score", 0.0)
            # Truncate long content for readability
            if len(content) > 200:
                content = content[:200] + "..."
            result_text += f"{i}. {content}\n(Relevance: {score:.2f})\n\n"
        
        return result_text.strip()
        
    except Exception as e:
        logger.error(f"❌ Error in vector search: {e}")
        return f"Error: Vector search failed - {str(e)}"


async def handle_get_pincode_data_tool(parameters: Dict[str, Any]) -> str:
    """
    Handle get pincode data tool calls
    
    Args:
        parameters: Tool parameters containing 'pincode' and/or 'city'
        
    Returns:
        String containing pincode data
    """
    try:
        pincode = parameters.get("pincode", "")
        city = parameters.get("city", "")
        
        logger.info(f"📍 Getting pincode data for pincode: {pincode}, city: {city}")
        
        # Get pincode data
        pincode_data = await get_pincode_data(pincode=pincode, city=city)
        
        # Parse the string result back to list
        import json
        try:
            parsed_data = json.loads(pincode_data) if isinstance(pincode_data, str) else pincode_data
        except json.JSONDecodeError:
            parsed_data = []
        
        if not parsed_data:
            search_criteria = []
            if pincode:
                search_criteria.append(f"pincode '{pincode}'")
            if city:
                search_criteria.append(f"city '{city}'")
            
            criteria_text = " and ".join(search_criteria) if search_criteria else "the specified criteria"
            return f"No pincode data found for {criteria_text}"
        
        # Format results as a readable string
        result_text = f"Found {len(parsed_data)} pincode record(s):\n\n"
        
        for i, data in enumerate(parsed_data, 1):
            result_text += f"{i}. Pincode: {data.get('pincode', 'N/A')}\n"
            result_text += f"   City: {data.get('city', 'N/A')}\n"
            result_text += f"   Home Scan: {data.get('home_scan', 'N/A')}\n"
            
            clinic_1 = data.get('clinic_1', '')
            clinic_2 = data.get('clinic_2', '')
            
            if clinic_1:
                result_text += f"   Clinic 1: {clinic_1}\n"
            if clinic_2:
                result_text += f"   Clinic 2: {clinic_2}\n"
            
            result_text += "\n"
        
        return result_text.strip()
        
    except Exception as e:
        logger.error(f"❌ Error in get pincode data: {e}")
        return f"Error: Get pincode data failed - {str(e)}"



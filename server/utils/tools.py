

import pandas as pd
import json
from typing import Dict, List, Optional, Any
from loguru import logger
from model.model import PincodeData, KnowledgeBase
from utils.analyst import vector_search, generate_embedding

async def extract_pincode_data() -> List[Dict]:
    """
    Extract pincode data from Excel file and return a list.
    Returns a list of dictionaries with keys: pincode, home_scan, clinic_1, clinic_2, city
    """
    try:
        # Read Excel file
        df = pd.read_excel('pincode_data(2).xlsx')
        
        logger.info(f"Successfully read pincode_data(2).xlsx with {len(df)} rows")
        
        # Initialize result list
        result = []
        
        # Process file
        for index, row in df.iterrows():
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


async def group_pincode_data_by_city_and_store() -> Dict[str, Any]:
    """
    Group pincode data by city and store in KnowledgeBase with embeddings
    
    Returns:
        Dict containing summary of the operation
    """
    try:
        logger.info("🏙️ Starting to group pincode data by city and store in KnowledgeBase")
        
        # Extract pincode data
        pincode_data = await extract_pincode_data()
        logger.info(f"📊 Extracted {len(pincode_data)} pincode records")
        
        # Group by city
        city_groups = {}
        for record in pincode_data:
            city = record.get("city", "").strip()
            if not city:  # Skip records without city
                continue
                
            if city not in city_groups:
                city_groups[city] = []
            city_groups[city].append(record)
        
        logger.info(f"🏙️ Grouped data into {len(city_groups)} cities")
        
        # Create KnowledgeBase entries for each city
        knowledge_base_entries = []
        
        for city, records in city_groups.items():
            # Create content string for this city
            content = f"Pincode and clinic information for {city}:\n\n"
            
            for i, record in enumerate(records, 1):
                content += f"{i}. Pincode: {record['pincode']}\n"
                content += f"   Home Scan Available: {record['home_scan']}\n"
                
                if record.get('clinic_1'):
                    content += f"   Clinic 1: {record['clinic_1']}\n"
                if record.get('clinic_2'):
                    content += f"   Clinic 2: {record['clinic_2']}\n"
                
                content += "\n"
            
            # Generate embedding for the content
            logger.info(f"🔍 Generating embedding for {city} ({len(records)} records)")
            embedding = generate_embedding(content)
            
            # Create KnowledgeBase entry
            kb_entry = KnowledgeBase(
                content=content,
                embedding=embedding
            )
            knowledge_base_entries.append(kb_entry)
        
        # Clear existing KnowledgeBase entries (optional - remove if you want to keep existing data)
     
        # Insert new entries
        logger.info(f"💾 Inserting {len(knowledge_base_entries)} KnowledgeBase entries")
        await KnowledgeBase.insert_many(knowledge_base_entries)
        
        # Prepare summary
        summary = {
            "total_pincode_records": len(pincode_data),
            "cities_processed": len(city_groups),
            "knowledge_base_entries_created": len(knowledge_base_entries),
            "cities": list(city_groups.keys())
        }
        
        logger.info(f"✅ Successfully stored pincode data in KnowledgeBase")
        logger.info(f"📊 Summary: {summary}")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error grouping and storing pincode data: {e}")
        return {"error": str(e)}


async def handle_tool_call(tool_call_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle VAPI tool call requests
    
    Args:
        tool_call_data: The tool call data from VAPI
        
    Returns:
        Dict containing the tool call result in VAPI format
    """
    try:
        # Log the full tool call data structure
        logger.info(f"🔍 Full tool call data: {tool_call_data}")
        
        # Extract tool call information
        tool_call = tool_call_data.get("toolCall", {})
        logger.info(f"🔍 Extracted tool_call: {tool_call}")
        
        tool_name = tool_call.get("function", {}).get("name", "")
        # VAPI uses 'arguments' instead of 'parameters' in the toolCall structure
        tool_parameters = tool_call.get("function", {}).get("arguments", {})
        tool_call_id = tool_call.get("id", "")
        
        logger.info(f"🔧 Processing tool call: {tool_name} with ID: {tool_call_id}")
        logger.info(f"📋 Tool parameters: {tool_parameters}")
        logger.info(f"📋 Tool parameters type: {type(tool_parameters)}")
        logger.info(f"📋 Tool parameters keys: {list(tool_parameters.keys()) if isinstance(tool_parameters, dict) else 'Not a dict'}")
        
        # Route to appropriate tool function
        if tool_name == "knowbase":
            result_string = await handle_vector_search_tool(tool_parameters)
        # elif tool_name == "get_pincode_data":
        #     result_string = await handle_get_pincode_data_tool(tool_parameters)
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
        logger.info(f"🔍 Vector search tool received parameters: {parameters}")
        logger.info(f"🔍 Parameters type: {type(parameters)}")
        logger.info(f"🔍 Parameters keys: {list(parameters.keys()) if isinstance(parameters, dict) else 'Not a dict'}")
        
        query = parameters.get("query", "")
        logger.info(f"🔍 Extracted query: '{query}'")
        
        if not query:
            return "Error: Query parameter is required for vector search"
        
        logger.info(f"🔍 Performing vector search for query: {query}")
        
        # Perform vector search
        search_results = await vector_search(query)
        
        if not search_results:
            return f"No results found for query: '{query}'"
        
        # Return only the content from search results
        contents = []
        for result in search_results:
            content = result.get("content", "")
            if content:
                contents.append(content)
        
        return "\n\n".join(contents)
        
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



import litellm
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
        df = pd.read_excel("pincode_data(2).xlsx")

        logger.info(f"Successfully read pincode_data(2).xlsx with {len(df)} rows")

        # Initialize result list
        result = []

        # Process file
        for index, row in df.iterrows():
            pincode = str(row["pincode"]).strip() if pd.notna(row["pincode"]) else ""
            home_scan = (
                str(row["home_scan_available"]).strip()
                if pd.notna(row["home_scan_available"])
                else ""
            )
            clinic_1 = (
                str(row["nearby clinic_1_display_name"]).strip()
                if pd.notna(row["nearby clinic_1_display_name"])
                else ""
            )
            clinic_2 = (
                str(row["nearby clinic_2_display_name"]).strip()
                if pd.notna(row["nearby clinic_2_display_name"])
                else ""
            )
            city = str(row["city"]).strip() if pd.notna(row["city"]) else ""

            # Skip if pincode is empty
            if not pincode:
                continue

            # Only add if at least one clinic exists
            if clinic_1 or clinic_2:

                result.append(
                    {
                        "pincode": pincode,
                        "home_scan": home_scan,
                        "clinic_1": clinic_1 if clinic_1 else "",
                        "clinic_2": clinic_2 if clinic_2 else "",
                        "city": city,
                    }
                )

        logger.info(f"Extracted {len(result)} total pincode entries")

        return result

    except Exception as e:
        logger.error(f"Error processing pincode data: {e}")
        raise e




# Saves pincode data to pincode schema
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
            city=data["city"],
        )
        pincode_documents.append(pincode_doc)

    # Insert all documents
    await PincodeData.insert_many(pincode_documents)
    logger.info(f"Saved {len(pincode_documents)} pincode data to the database")

    # Return all pincode data from database
    pincode_data = await PincodeData.find().to_list()
    logger.info(f"Found {len(pincode_data)} pincode data in the database")
    return pincode_data




#  store pincode data to vector store
async def group_pincode_data_by_city_and_store() -> Dict[str, Any]:
    """
    Group pincode data by city and store in KnowledgeBase with embeddings

    Returns:
        Dict containing summary of the operation
    """
    try:
        logger.info(
            "🏙️ Starting to group pincode data by city and store in KnowledgeBase"
        )

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

                if record.get("clinic_1"):
                    content += f"   Clinic 1: {record['clinic_1']}\n"
                if record.get("clinic_2"):
                    content += f"   Clinic 2: {record['clinic_2']}\n"

                content += "\n"

            # Generate embedding for the content
            logger.info(f"🔍 Generating embedding for {city} ({len(records)} records)")
            embedding = generate_embedding(content)

            # Create KnowledgeBase entry
            kb_entry = KnowledgeBase(content=content, embedding=embedding)
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
            "cities": list(city_groups.keys()),
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
        logger.info(
            f"📋 Tool parameters keys: {list(tool_parameters.keys()) if isinstance(tool_parameters, dict) else 'Not a dict'}"
        )

        # Route to appropriate tool function
        if tool_name == "Knowledgebase":
            result_string = await handle_vector_search_tool(tool_parameters)
        elif tool_name == "nearby_clinic":
            result_string = await handle_nearby_clinic_tool(tool_parameters)
        else:
            logger.warning(f"⚠️ Unknown tool: {tool_name}")
            result_string = f"Error: Unknown tool '{tool_name}'. Available tools: Knowledgebase, nearby_clinic"

        return {"toolCallId": tool_call_id, "result": result_string}

    except Exception as e:
        logger.error(f"❌ Error handling tool call: {e}")
        return {
            "toolCallId": tool_call_data.get("toolCall", {}).get("id", ""),
            "result": f"Error: {str(e)}",
        }


async def handle_nearby_clinic_tool(parameters: Dict[str, Any]) -> str:
    """
    Handle nearby clinic tool calls

    Args:
        parameters: Tool parameters containing 'pincode' and/or 'city'

    Returns:
        String containing nearby clinic data
    """
    try:
        logger.info(f"🏥 Nearby clinic tool received parameters: {parameters}")
        logger.info(f"🏥 Parameters type: {type(parameters)}")
        logger.info(
            f"🏥 Parameters keys: {list(parameters.keys()) if isinstance(parameters, dict) else 'Not a dict'}"
        )

        pincode = parameters.get("pincode", "")
        city = parameters.get("city", "")
        
        logger.info(f"🏥 Extracted pincode: '{pincode}', city: '{city}'")

        # Call the nearby clinic function
        result = await get_near_by_clinic_data(
            pincode=pincode if pincode else None,
            city=city if city else None
        )

        return result

    except Exception as e:
        logger.error(f"❌ Error in nearby clinic tool: {e}")
        return f"Error: Nearby clinic search failed - {str(e)}"


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
        logger.info(
            f"🔍 Parameters keys: {list(parameters.keys()) if isinstance(parameters, dict) else 'Not a dict'}"
        )

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

        # rag call
        contents = "\n\n".join(contents)
        rag_res = await rag_call(query, contents)
        return rag_res

    except Exception as e:
        logger.error(f"❌ Error in vector search: {e}")
        return f"Error: Vector search failed - {str(e)}"


rag_prompt = """
## Identity
You are an AI assistant that processes queries from makeO toothsi call agents and generates responses using ONLY the provided context data. Your responses will be used by call agents like Ananya to assist customers with dental services, clinic locations, and treatment information.

## Core Rules
1. **Use ONLY the provided context** - Never add information from outside sources or your general knowledge
2. **Answer directly and conversationally** - Provide clear, helpful responses that call agents can easily relay to customers
3. **Handle data limitations professionally** - Guide users when information is incomplete or unclear
4. **If information is not in context** - Respond with "I don't know"
5. **Prioritize customer experience** - Format responses to sound natural when spoken over phone

## Response Guidelines

### Standard Responses
- Give direct answers from the context data
- Keep responses clear and professional (1-3 sentences typically)
- Use exact information as found in the provided data
- Format responses so call agents can easily read them to customers in both Hindi and English contexts
- Include specific details like addresses, phone numbers, timings when available

### Handling Location-Based Queries

#### For Exact Pincode Match
- Provide clinic name, address, and contact details if available
- List maximum 2-3 closest options
- Include any special services or facilities mentioned

#### For Incorrect/Missing Pincode
**Template Response**: 
"I think the pincode you provided might be incorrect. Can you tell me the city name also so I can find the exact clinics for you? From the available data, I can see toothsi centers in nearby areas like [list 2-3 nearby locations with clinic names]."

#### For City-Only Queries
**Template Response**:
"There are several toothsi experience centers in [city name]. Here are some options: [list 2-3 centers with areas/localities]. Could you provide your specific pincode so I can tell you the exact nearby clinics?"

#### For No Results Found
"I don't have information about toothsi centers in that area. You might want to check our main centers or consider a home scan option."

### Dental Service-Specific Responses

#### Treatment Information
- Provide exact details from context about procedures, duration, pricing
- Include any eligibility criteria or prerequisites mentioned
- Mention follow-up requirements if specified

#### Pricing Queries
- Give exact pricing ranges from context
- Include EMI options if mentioned
- Always note "final pricing after assessment" when applicable

#### Appointment/Scan Booking
- Provide available time slots if in context
- Include booking process details
- Mention required documents or preparations

## Response Format Templates

### Successful Location Query
**Example**: "For pincode 110001, the nearest toothsi experience center is located at [exact address from context]. You can contact them at [phone number]. They offer [services from context]."

### Incorrect Pincode Response  
**Example**: "I think the pincode you provided might be incorrect. Can you tell me the city name also so I can find the exact clinics for you? I found toothsi centers in nearby areas like pincode 110002 with Delhi Center and pincode 110003 with CP Center."

### City-Wide Query Response
**Example**: "There are several toothsi experience centers in Delhi. Here are some options: Connaught Place Center, South Delhi Center, and Gurgaon Center. Could you provide your specific pincode so I can tell you the exact nearby clinics?"

### Treatment Information Response
**Example**: "Based on the available information, [treatment name] typically takes [duration from context] and costs between [price range from context]. The process involves [steps from context]."

### No Information Available
**Example**: "I don't know." or "I don't have that information in my current database."

## Special Handling for Common Dental Queries

### Home Scan vs Center Scan
- Provide exact differences from context data
- Include availability in their area if mentioned
- List benefits of each option from context

### Treatment Duration & Process
- Give specific timeframes from context
- Include any variation factors mentioned
- Provide step-by-step process if available

### Pricing & EMI Options
- Share exact pricing tiers from context
- Include EMI calculation details if provided
- Mention any ongoing offers from context data

### Doctor & Clinic Information  
- Provide doctor qualifications if in context
- Include clinic facilities and equipment details
- Mention success rates or certifications from context

## Response Quality Standards

### For Call Agent Usage:
- **Conversational tone**: Responses should sound natural when read aloud
- **Clear pronunciation**: Avoid complex terms that are hard to say over phone  
- **Logical flow**: Structure information in the order agents would naturally present it
- **Action-oriented**: Include clear next steps when appropriate

### For Customer Experience:
- **Helpful guidance**: Always try to move the customer toward a solution
- **Professional confidence**: Use definitive language from context data
- **Empathetic approach**: Acknowledge when you can't help and offer alternatives

## Quality Assurance Checklist

Before providing any response, verify:
- [ ] Information comes only from provided context
- [ ] Response is easy for call agent to read aloud
- [ ] Location information includes specific details (address, pincode)
- [ ] Pricing information includes necessary disclaimers
- [ ] Alternative options are provided when exact match isn't found
- [ ] Response guides toward next logical step in customer journey

## Error Handling

### When Context is Unclear:
"I have some information about [topic], but I need more specific details to give you the exact answer. Could you clarify [specific question]?"

### When Multiple Matches Exist:
"I found several options for [request]. Here are the top matches: [list with distinguishing details]. Which one would work best for your location/needs?"

### When Partial Information Available:
"I have partial information about [topic]: [available details from context]. For complete details, you may need to contact our center directly at [contact info if available]."

## Important Notes
- Only use information from the provided context data
- Never make assumptions or add external knowledge  
- Format responses for easy relay by call agents to customers
- Be helpful in guiding users to provide more specific information when needed
- When in doubt, always say "I don't know"
- Remember responses will be used in both Hindi and English conversations
- Prioritize actionable information that moves customers toward booking scans or consultations

"""


async def rag_call(query: str, contents: str) -> str:
    """
    RAG call
    """
    res = litellm.completion(
        model="openai/gpt-5-nano",
        messages=[
            {"role": "system", "content": rag_prompt},
            {
                "role": "user",
                "content": "Context: " + contents + "\n\n" + "Query: " + query,
            },
        ],
    )
    return res.choices[0].message.content




async def get_near_by_clinic_data(pincode: Optional[str] = None, city: Optional[str] = None) -> str:
    """
    Get nearby clinic data based on city and/or pincode
    
    Args:
        pincode: Optional pincode to search for
        city: Optional city name to search for
        
    Returns:
        String containing clinic information
    """
    try:
        from difflib import get_close_matches
        
        logger.info(f"🏥 Getting nearby clinic data for pincode: {pincode}, city: {city}")
        
        # If both pincode and city are provided, search for exact match
        if pincode and city:
            # First, try exact city match
            query_filter = {"pincode": pincode, "city": city}
            exact_results = await PincodeData.find(query_filter).to_list()
            
            if exact_results:
                logger.info(f"✅ Found exact match for pincode {pincode} and city {city}")
                return _format_clinic_results(exact_results, f"Exact match for pincode {pincode} in {city}")
            
            # If no exact match, try fuzzy search for city name
            logger.info(f"🔍 No exact city match found, trying fuzzy search for city: {city}")
            
            # Get all unique cities from database for fuzzy matching
            all_cities = await PincodeData.distinct("city")
            logger.info(f"📋 Available cities in database: {all_cities[:10]}...")  # Log first 10 cities
            
            # Find closest city match using fuzzy search
            city_matches = get_close_matches(
                city.title(),  # Convert to title case for matching
                [c.title() for c in all_cities if c],  # Convert all cities to title case
                n=3,  # Get top 3 matches
                cutoff=0.6  # Minimum similarity threshold
            )
            
            if city_matches:
                best_match = city_matches[0]
                logger.info(f"🎯 Best fuzzy match for '{city}': '{best_match}'")
                
                # Search with the best matching city
                fuzzy_query_filter = {"pincode": pincode, "city": best_match}
                fuzzy_results = await PincodeData.find(fuzzy_query_filter).to_list()
                
                if fuzzy_results:
                    return _format_clinic_results(fuzzy_results, f"Found match for pincode {pincode} in {best_match} (fuzzy match for '{city}')")
            
            # If still no match, return nearby clinics from the same pincode
            logger.info(f"🔍 No city match found, searching for any clinics in pincode {pincode}")
            pincode_only_results = await PincodeData.find({"pincode": pincode}).limit(5).to_list()
            
            if pincode_only_results:
                return _format_clinic_results(pincode_only_results, f"Found clinics in pincode {pincode} (city '{city}' not found)")
            
            return f"No clinics found for pincode {pincode} and city '{city}'. Please verify the pincode and city name."
        
        # If only city is provided, get 5 clinics from that city
        elif city and not pincode:
            # Try exact city match first
            exact_results = await PincodeData.find({"city": city}).limit(5).to_list()
            
            if exact_results:
                logger.info(f"✅ Found exact match for city: {city}")
                return _format_clinic_results(exact_results, f"Clinics in {city}")
            
            # Try fuzzy search for city
            logger.info(f"🔍 No exact city match found, trying fuzzy search for city: {city}")
            
            all_cities = await PincodeData.distinct("city")
            city_matches = get_close_matches(
                city.title(),
                [c.title() for c in all_cities if c],
                n=3,
                cutoff=0.6
            )
            
            if city_matches:
                best_match = city_matches[0]
                logger.info(f"🎯 Best fuzzy match for '{city}': '{best_match}'")
                
                fuzzy_results = await PincodeData.find({"city": best_match}).limit(5).to_list()
                
                if fuzzy_results:
                    return _format_clinic_results(fuzzy_results, f"Clinics in {best_match} (fuzzy match for '{city}')")
            
            return f"No clinics found for city '{city}'. Please check the city name spelling."
        
        # If only pincode is provided, get clinics for that pincode
        elif pincode and not city:
            results = await PincodeData.find({"pincode": pincode}).limit(5).to_list()
            
            if results:
                return _format_clinic_results(results, f"Clinics in pincode {pincode}")
            
            return f"No clinics found for pincode {pincode}. Please verify the pincode."
        
        # If neither is provided, return error
        else:
            return "Error: Please provide either city or pincode (or both) to search for nearby clinics."
    
    except Exception as e:
        logger.error(f"❌ Error getting nearby clinic data: {e}")
        return f"Error: Failed to get clinic data - {str(e)}"


def _format_clinic_results(results: List[PincodeData], header: str) -> str:
    """
    Format clinic results into a readable string
    
    Args:
        results: List of PincodeData objects
        header: Header text for the results
        
    Returns:
        Formatted string with clinic information
    """
    if not results:
        return "No clinic data found."
    
    result_text = f"{header}:\n\n"
    
    for i, data in enumerate(results, 1):
        result_text += f"{i}. Pincode: {data.pincode}\n"
        result_text += f"   City: {data.city}\n"
        result_text += f"   Home Scan Available: {data.home_scan}\n"
        
        if data.clinic_1:
            result_text += f"   Clinic 1: {data.clinic_1}\n"
        if data.clinic_2:
            result_text += f"   Clinic 2: {data.clinic_2}\n"
        
        result_text += "\n"
    
    return result_text.strip()
    
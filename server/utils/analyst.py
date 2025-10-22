from litellm import completion, embedding
import os
from pydantic import BaseModel

from loguru import logger


TRANSCRIPT_ANALYSIS_PROMPT = """
You are an AI assistant that analyzes phone call transcripts. Please analyze the following transcript and provide output in JSON format with the following fields:

1. *summary*:  
   - Provide a concise summary of the call.  
   - Mention whether the outcome was positive (e.g., booking confirmed, customer satisfied) or negative (e.g., lead dropped, issue unresolved).  
   - Highlight key details such as verification completed, questions answered, and the final end point of the conversation.

2. *quality_score*:  
   - Scoring should be broken down into 4 weighted checks:  
     - Verification of name done: 2.5  
     - Pin code / city mentioned by user: 2.5  
     - Questions and answers discussed: 2.5  
     - Scan confirmed: 2.5  
   - If the scan is confirmed, the total quality score must always be *10.0*.  
   - Otherwise, sum the applicable components to determine the final score.

3. *customer_intent*:  
   - Capture the customer’s purpose in keywords.  
   - Include type of issue (e.g., teeth alignment query, payment issue, appointment scheduling).  
   - Include type of booking or request (e.g., scan booking, reschedule, inquiry).  
   - Mention the overall status of the conversation (e.g., lead, dropped, in process, call me later).

### Output JSON fields:
- summary: string  
- quality_score: float (0.0 to 10.0)  
- customer_intent: string


"""


class AnalystResult(BaseModel):
    summary: str
    quality_score: float
    customer_intent: str


def analyze_transcript(transcript: str) -> AnalystResult:
    """Analyze transcript"""
    try:
        # Log input transcript
        logger.info(f"📝 Analyzing transcript (length: {len(transcript)} characters)")
    

        response = completion(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="openai/gpt-5-nano",
            messages=[
                {"content": TRANSCRIPT_ANALYSIS_PROMPT, "role": "system"},
                {"content": transcript, "role": "user"},
            ],
            response_format=AnalystResult,
        )

        # Parse the response content as AnalystResult
        content = response.choices[0].message.content
        if isinstance(content, AnalystResult):
            result = content
        else:
            # If it's a string, try to parse it as JSON
            import json

            data = json.loads(content)
            result = AnalystResult(**data)

        # Log the generated response
        logger.info(f"✅ Transcript analysis completed successfully")
        logger.info(f"📊 Generated response:")

        return result

    except Exception as e:
        logger.error(f"❌ Error analyzing transcript: {e}")
        # Return a default result if analysis fails
        default_result = AnalystResult(
            summary="Analysis failed", quality_score=0.0, customer_intent="unknown"
        )
        logger.error(f"🔄 Returning default result due to error: {default_result}")
        return default_result



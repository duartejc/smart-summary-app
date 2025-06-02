import json
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal

from app.services.ai_service import AIService
from app.core.security import get_current_user
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

class GenerateRequest(BaseModel):
    model_type: Literal["completion", "chat"] = "completion"
    params: Dict[str, Any]
    stream: bool = False

async def event_generator(ai_service, model_type: str, params: Dict[str, Any]):
    """Generate Server-Sent Events from the AI service streaming response."""
    try:
        async for chunk in ai_service.generate_stream(
            model_type=model_type,
            params=params,
        ):
            # The chunk is already a JSON string from AIService
            try:
                # Parse the JSON to ensure it's valid
                chunk_data = json.loads(chunk)
                if 'error' in chunk_data:
                    yield f"event: error\ndata: {json.dumps(chunk_data)}\n\n"
                else:
                    yield f"data: {chunk}\n\n"
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in chunk: {chunk}")
                continue
                
    except Exception as e:
        error_msg = f"Error in event generator: {str(e)}"
        logger.error(error_msg)
        yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"
    finally:
        yield "event: end\ndata: {}\n\n"
        if 'ai_service' in locals():
            await ai_service.close()

@router.post("/generate")
async def generate(
    request: Request,
    data: GenerateRequest
):
    """
    Generate AI response based on the provided prompt and parameters.
    
    Supports both streaming (SSE) and non-streaming responses based on the 'stream' parameter.
    """
    try:
        # Initialize services
        ai_service = AIService()

        if data.stream:
            # Return streaming response
            return StreamingResponse(
                event_generator(
                    ai_service=ai_service,
                    model_type=data.model_type,
                    params=data.params,
                ),
                media_type="text/event-stream",
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                }
            )
        else:
            # Standard non-streaming response
            response = await ai_service.generate_response(
                model_type=data.model_type,
                params=data.params,
            )
            await ai_service.close()
            return {"response": response}
            
    except Exception as e:
        logger.error(f"Error in generate endpoint: {str(e)}")
        if 'ai_service' in locals():
            await ai_service.close()
        raise HTTPException(status_code=500, detail=str(e))

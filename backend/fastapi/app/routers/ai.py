"""
AI/LLM services router for OpenAI integration, embeddings, and vector search
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

import openai
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.models.ai import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorSearchResult,
    ModelConfig,
    LLMProvider,
    ModelType,
    ModelStatus,
    ModelListResponse,
)

logger = get_logger(__name__)

router = APIRouter()

# Initialize OpenAI client
openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# In-memory vector store (in production, use proper vector database)
_vector_store = {}
_embedding_cache = {}


@router.post("/chat", response_model=ChatResponse, summary="Chat Completion")
async def chat_completion(request: ChatRequest) -> ChatResponse:
    """
    Generate chat completion using OpenAI API

    Args:
        request: Chat completion request

    Returns:
        ChatResponse: Chat completion response
    """
    try:
        start_time = time.time()

        # Prepare messages for OpenAI API
        messages = []
        for msg in request.messages:
            messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                    "name": msg.name,
                    "function_call": msg.function_call,
                    "tool_calls": msg.tool_calls,
                }
            )

        # Set model configuration
        model_config = request.model_config or get_default_model_config()

        # Make OpenAI API call
        response = await openai_client.chat.completions.create(
            model=model_config.model_name or settings.OPENAI_MODEL,
            messages=messages,
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            top_p=model_config.top_p,
            frequency_penalty=model_config.frequency_penalty,
            presence_penalty=model_config.presence_penalty,
            stop=model_config.stop_sequences,
            stream=model_config.stream,
            response_format=model_config.response_format,
            tools=model_config.tools,
            tool_choice=model_config.tool_choice,
            **model_config.custom_parameters,
        )

        response_time = (time.time() - start_time) * 1000

        # Create response message
        assistant_message = ChatMessage(
            role=response.choices[0].message.role,
            content=response.choices[0].message.content,
            name=response.choices[0].message.name,
            function_call=response.choices[0].message.function_call,
            tool_calls=response.choices[0].message.tool_calls,
            timestamp=datetime.utcnow(),
            metadata={"model": model_config.model_name},
        )

        # Create usage information
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        logger.info(
            "Chat completion generated",
            model=model_config.model_name,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            response_time_ms=response_time,
        )

        return ChatResponse(
            success=True,
            message="Chat completion generated successfully",
            chat_message=assistant_message,
            model=model_config.model_name or settings.OPENAI_MODEL,
            usage=usage,
            finish_reason=response.choices[0].finish_reason,
            response_time_ms=response_time,
            session_id=request.session_id,
            metadata=request.metadata,
        )

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate chat completion"
        )


@router.post("/chat/stream", summary="Streaming Chat Completion")
async def chat_completion_stream(request: ChatRequest):
    """
    Generate streaming chat completion using OpenAI API

    Args:
        request: Chat completion request

    Returns:
        StreamingResponse: Server-sent events stream
    """
    try:
        # Prepare messages for OpenAI API
        messages = []
        for msg in request.messages:
            messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                    "name": msg.name,
                    "function_call": msg.function_call,
                    "tool_calls": msg.tool_calls,
                }
            )

        # Set model configuration with streaming enabled
        model_config = request.model_config or get_default_model_config()
        model_config.stream = True

        async def generate_stream():
            try:
                stream = await openai_client.chat.completions.create(
                    model=model_config.model_name or settings.OPENAI_MODEL,
                    messages=messages,
                    temperature=model_config.temperature,
                    max_tokens=model_config.max_tokens,
                    top_p=model_config.top_p,
                    frequency_penalty=model_config.frequency_penalty,
                    presence_penalty=model_config.presence_penalty,
                    stop=model_config.stop_sequences,
                    stream=True,
                    tools=model_config.tools,
                    tool_choice=model_config.tool_choice,
                    **model_config.custom_parameters,
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield f"data: {chunk.choices[0].delta.content}\n\n"

                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Streaming chat completion error: {e}")
                yield f"data: ERROR: {str(e)}\n\n"

        logger.info(
            "Started streaming chat completion",
            model=model_config.model_name or settings.OPENAI_MODEL,
            session_id=request.session_id,
        )

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Failed to start streaming chat completion: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start streaming chat completion"
        )


@router.post(
    "/completions", response_model=CompletionResponse, summary="Text Completion"
)
async def text_completion(request: CompletionRequest) -> CompletionResponse:
    """
    Generate text completion using OpenAI API

    Args:
        request: Text completion request

    Returns:
        CompletionResponse: Text completion response
    """
    try:
        start_time = time.time()

        # Set model configuration
        model_config = request.model_config or get_default_model_config()

        # Make OpenAI API call
        response = await openai_client.completions.create(
            model=model_config.model_name or settings.OPENAI_MODEL,
            prompt=request.prompt,
            suffix=request.suffix,
            max_tokens=request.max_tokens or model_config.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stop=request.stop_sequences,
            user=request.user,
        )

        response_time = (time.time() - start_time) * 1000

        # Create usage information
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        logger.info(
            "Text completion generated",
            model=model_config.model_name or settings.OPENAI_MODEL,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            response_time_ms=response_time,
        )

        return CompletionResponse(
            success=True,
            message="Text completion generated successfully",
            text=response.choices[0].text,
            model=model_config.model_name or settings.OPENAI_MODEL,
            usage=usage,
            finish_reason=response.choices[0].finish_reason,
            response_time_ms=response_time,
            metadata=request.context,
        )

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error(f"Text completion failed: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate text completion"
        )


@router.post(
    "/embeddings", response_model=EmbeddingResponse, summary="Generate Embeddings"
)
async def generate_embeddings(request: EmbeddingRequest) -> EmbeddingResponse:
    """
    Generate text embeddings using OpenAI API

    Args:
        request: Embedding generation request

    Returns:
        EmbeddingResponse: Embedding generation response
    """
    try:
        start_time = time.time()

        # Handle cache for repeated embeddings
        cache_key = (
            str(request.input)
            if isinstance(request.input, str)
            else str(hash(tuple(request.input)))
        )
        if cache_key in _embedding_cache:
            cached_embeddings = _embedding_cache[cache_key]
            response_time = (time.time() - start_time) * 1000

            logger.info(
                "Embeddings retrieved from cache",
                input_type="text" if isinstance(request.input, str) else "batch",
                embedding_count=len(cached_embeddings),
                response_time_ms=response_time,
            )

            return EmbeddingResponse(
                success=True,
                message="Embeddings retrieved from cache",
                embeddings=cached_embeddings,
                model="text-embedding-ada-002",
                usage={"prompt_tokens": 0, "total_tokens": 0},
                dimensions=len(cached_embeddings[0]) if cached_embeddings else 1536,
                response_time_ms=response_time,
            )

        # Set model configuration
        model_config = request.model_config or get_default_embedding_config()

        # Make OpenAI API call
        response = await openai_client.embeddings.create(
            model=model_config.model_name or "text-embedding-ada-002",
            input=request.input,
            encoding_format=request.encoding_format,
            user=request.user,
            dimensions=request.dimensions,
        )

        response_time = (time.time() - start_time) * 1000

        # Extract embeddings
        embeddings = [item.embedding for item in response.data]

        # Cache embeddings
        _embedding_cache[cache_key] = embeddings

        # Create usage information
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "total_tokens": response.usage.prompt_tokens,
        }

        logger.info(
            "Embeddings generated",
            model="text-embedding-ada-002",
            input_type="text" if isinstance(request.input, str) else "batch",
            embedding_count=len(embeddings),
            dimensions=len(embeddings[0]) if embeddings else 0,
            response_time_ms=response_time,
        )

        return EmbeddingResponse(
            success=True,
            message="Embeddings generated successfully",
            embeddings=embeddings,
            model="text-embedding-ada-002",
            usage=usage,
            dimensions=len(embeddings[0]) if embeddings else 1536,
            response_time_ms=response_time,
            metadata=request.model_config.metadata if request.model_config else {},
        )

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {str(e)}")
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate embeddings")


@router.post(
    "/vector/search",
    response_model=VectorSearchResponse,
    summary="Vector Similarity Search",
)
async def vector_search(request: VectorSearchRequest) -> VectorSearchResponse:
    """
    Perform vector similarity search

    Args:
        request: Vector search request

    Returns:
        VectorSearchResponse: Vector search results
    """
    try:
        start_time = time.time()

        # Generate query embedding if not provided
        query_embedding = request.query_embedding
        query_embedding_generated = False

        if not query_embedding:
            embedding_request = EmbeddingRequest(
                input=request.query, model_config=request.model_config
            )
            embedding_response = await generate_embeddings(embedding_request)
            query_embedding = embedding_response.embeddings[0]
            query_embedding_generated = True

        # Perform similarity search
        results = []
        collection = _vector_store.get(request.collection, {})

        for doc_id, doc_data in collection.items():
            doc_embedding = doc_data.get("embedding")
            if not doc_embedding:
                continue

            # Calculate cosine similarity
            similarity = cosine_similarity(query_embedding, doc_embedding)

            if similarity >= request.threshold:
                # Apply filters
                if request.filters:
                    if not all(
                        doc_data.get(k) == v for k, v in request.filters.items()
                    ):
                        continue

                result = VectorSearchResult(
                    id=doc_id,
                    content=doc_data.get("content", ""),
                    similarity=similarity,
                    metadata=doc_data.get("metadata", {}),
                    embedding=doc_embedding if request.include_embeddings else None,
                )
                results.append(result)

        # Sort by similarity and limit results
        results.sort(key=lambda x: x.similarity, reverse=True)
        results = results[: request.limit]

        query_time = (time.time() - start_time) * 1000

        logger.info(
            "Vector search completed",
            collection=request.collection,
            results_count=len(results),
            query_time_ms=query_time,
            threshold=request.threshold,
        )

        return VectorSearchResponse(
            success=True,
            message="Vector search completed successfully",
            results=results,
            total=len(collection),
            query_time_ms=query_time,
            collection=request.collection,
            query_embedding_generated=query_embedding_generated,
            metadata={
                "query_length": len(request.query),
                "embedding_dimensions": len(query_embedding),
            },
        )

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform vector search")


@router.post("/vector/store", summary="Store Document with Embedding")
async def store_document_with_embedding(
    content: str,
    document_id: Optional[str] = None,
    collection: str = "default",
    metadata: Optional[Dict[str, Any]] = None,
    generate_embedding: bool = True,
) -> Dict[str, str]:
    """
    Store document with embedding in vector store

    Args:
        content: Document content
        document_id: Optional document ID (auto-generated if not provided)
        collection: Collection name
        metadata: Optional metadata
        generate_embedding: Whether to generate embedding

    Returns:
        Dict: Storage result
    """
    try:
        import uuid

        if not document_id:
            document_id = f"doc_{uuid.uuid4().hex[:8]}"

        embedding = None
        if generate_embedding:
            embedding_request = EmbeddingRequest(input=content)
            embedding_response = await generate_embeddings(embedding_request)
            embedding = embedding_response.embeddings[0]

        # Store document
        if collection not in _vector_store:
            _vector_store[collection] = {}

        _vector_store[collection][document_id] = {
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "Document stored in vector store",
            document_id=document_id,
            collection=collection,
            has_embedding=bool(embedding),
        )

        return {
            "status": "stored",
            "document_id": document_id,
            "collection": collection,
            "has_embedding": str(embedding is not None),
        }

    except Exception as e:
        logger.error(f"Failed to store document: {e}")
        raise HTTPException(status_code=500, detail="Failed to store document")


@router.get(
    "/models", response_model=ModelListResponse, summary="List Available Models"
)
async def list_models(
    provider: Optional[LLMProvider] = Query(
        default=None, description="Filter by provider"
    ),
    model_type: Optional[ModelType] = Query(
        default=None, description="Filter by model type"
    ),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> ModelListResponse:
    """
    List available AI models

    Args:
        provider: Filter by provider
        model_type: Filter by model type
        page: Page number for pagination
        page_size: Number of items per page

    Returns:
        ModelListResponse: Paginated list of models
    """
    try:
        # Get available models from OpenAI
        models = await openai_client.models.list()

        # Convert to ModelStatus objects
        model_statuses = []
        for model in models.data:
            # Determine model type based on model ID
            model_type_str = "chat"
            if "embedding" in model.id:
                model_type_str = "embedding"
            elif "text-" in model.id and "embedding" not in model.id:
                model_type_str = "completion"

            model_status = ModelStatus(
                provider=LLMProvider.OPENAI,
                model_name=model.id,
                status="available",
                last_checked=datetime.utcnow(),
                capabilities=[model_type_str],
            )
            model_statuses.append(model_status)

        # Apply filters
        if provider:
            model_statuses = [m for m in model_statuses if m.provider == provider]
        if model_type:
            model_statuses = [
                m for m in model_statuses if model_type.value in m.capabilities
            ]

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated_models = model_statuses[start:end]

        return ModelListResponse(
            items=paginated_models,
            total=len(model_statuses),
            page=page,
            page_size=page_size,
            total_pages=(len(model_statuses) + page_size - 1) // page_size,
            has_next=end < len(model_statuses),
            has_prev=page > 1,
        )

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve models")


# Helper functions
def get_default_model_config() -> ModelConfig:
    """Get default model configuration"""
    return ModelConfig(
        provider=LLMProvider.OPENAI,
        model_name=settings.OPENAI_MODEL,
        model_type=ModelType.CHAT,
        temperature=settings.OPENAI_TEMPERATURE,
        max_tokens=settings.OPENAI_MAX_TOKENS,
    )


def get_default_embedding_config() -> ModelConfig:
    """Get default embedding model configuration"""
    return ModelConfig(
        provider=LLMProvider.OPENAI,
        model_name="text-embedding-ada-002",
        model_type=ModelType.EMBEDDING,
        temperature=0.0,
        max_tokens=None,
    )


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    try:
        import numpy as np

        vec_a_np = np.array(vec_a)
        vec_b_np = np.array(vec_b)

        dot_product = np.dot(vec_a_np, vec_b_np)
        norm_a = np.linalg.norm(vec_a_np)
        norm_b = np.linalg.norm(vec_b_np)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    except ImportError:
        # Fallback without numpy
        if len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

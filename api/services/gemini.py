"""LLM API service for RAG answer generation (Gemini + OpenAI fallback)."""
import os
import logging
from typing import Generator, List, Dict, Any

logger = logging.getLogger(__name__)

# Try Gemini first, fallback to OpenAI
_gemini_configured = False
_openai_configured = False
_use_openai = False


def _ensure_configured():
    """Ensure LLM API is configured with API key."""
    global _gemini_configured, _openai_configured, _use_openai

    # Try Gemini first
    if not _gemini_configured:
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                _gemini_configured = True
                logger.info("Gemini API configured")
            except Exception as e:
                logger.warning(f"Gemini configuration failed: {e}")

    # Fallback to OpenAI
    if not _openai_configured:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                import openai
                openai.api_key = openai_key
                _openai_configured = True
                logger.info("OpenAI API configured as fallback")
            except Exception as e:
                logger.warning(f"OpenAI configuration failed: {e}")


def _build_prompt(query: str, context_chunks: List[Dict[str, Any]]) -> str:
    """Build the RAG prompt with context."""
    context_parts = []
    for i, chunk in enumerate(context_chunks[:5], 1):
        text = chunk.get("text", "")[:800]
        source_id = chunk.get("id", "unknown")
        context_parts.append(f"[Nguồn {i}] {text}\n(ID: {source_id})")

    context_text = "\n\n".join(context_parts)

    return f"""Bạn là chuyên gia về luật thuế Việt Nam. Nhiệm vụ của bạn là trả lời câu hỏi dựa trên ngữ cảnh được cung cấp từ các văn bản pháp luật.

## Ngữ cảnh từ các văn bản pháp luật:
{context_text}

## Câu hỏi của người dùng:
{query}

## Hướng dẫn trả lời:
1. Trả lời bằng tiếng Việt, rõ ràng và chính xác
2. Trích dẫn các điều luật, khoản, điểm cụ thể khi có thể
3. Nếu ngữ cảnh không đủ thông tin, hãy nói rõ điều đó
4. Không bịa đặt thông tin không có trong ngữ cảnh

## Trả lời:"""


def _generate_with_openai(prompt: str, stream: bool = False):
    """Generate using OpenAI API."""
    import openai

    client = openai.OpenAI()

    if stream:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    else:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024
        )
        return response.choices[0].message.content


def _generate_with_gemini(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    """Generate using Gemini API (non-streaming)."""
    import google.generativeai as genai

    model = genai.GenerativeModel(model_name)
    config = genai.GenerationConfig(temperature=0.3, max_output_tokens=1024)
    response = model.generate_content(prompt, generation_config=config)
    return response.text


def _generate_with_gemini_streaming(prompt: str, model_name: str = "gemini-2.0-flash"):
    """Generate using Gemini API (streaming)."""
    import google.generativeai as genai

    model = genai.GenerativeModel(model_name)
    config = genai.GenerationConfig(temperature=0.3, max_output_tokens=1024)
    response = model.generate_content(prompt, stream=True, generation_config=config)
    for chunk in response:
        if chunk.text:
            yield chunk.text


def generate_answer_streaming(
    query: str,
    context_chunks: List[Dict[str, Any]],
    model_name: str = "gemini-2.0-flash"
) -> Generator[str, None, None]:
    """
    Generate answer with streaming, with OpenAI fallback.

    Args:
        query: User's question
        context_chunks: Retrieved and reranked context chunks
        model_name: Gemini model to use

    Yields:
        Text chunks from the streaming response
    """
    _ensure_configured()
    prompt = _build_prompt(query, context_chunks)

    # Try Gemini first
    if _gemini_configured:
        try:
            for chunk in _generate_with_gemini_streaming(prompt, model_name):
                yield chunk
            return
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning(f"Gemini quota exceeded, falling back to OpenAI: {e}")
            else:
                logger.error(f"Gemini generation failed: {e}")

    # Fallback to OpenAI
    if _openai_configured:
        try:
            logger.info("Using OpenAI fallback for generation")
            for chunk in _generate_with_openai(prompt, stream=True):
                yield chunk
            return
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")

    yield "[Lỗi] Không thể tạo câu trả lời. Vui lòng thử lại sau."


def generate_answer(
    query: str,
    context_chunks: List[Dict[str, Any]],
    model_name: str = "gemini-2.0-flash"
) -> str:
    """
    Generate answer (non-streaming), with OpenAI fallback.

    Args:
        query: User's question
        context_chunks: Retrieved and reranked context chunks
        model_name: Gemini model to use

    Returns:
        Generated answer text
    """
    _ensure_configured()
    prompt = _build_prompt(query, context_chunks)

    # Try Gemini first
    if _gemini_configured:
        try:
            return _generate_with_gemini(prompt, model_name)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning(f"Gemini quota exceeded, falling back to OpenAI: {e}")
            else:
                logger.error(f"Gemini generation failed: {e}")

    # Fallback to OpenAI
    if _openai_configured:
        try:
            logger.info("Using OpenAI fallback for generation")
            return _generate_with_openai(prompt, stream=False)
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")

    return "[Lỗi] Không thể tạo câu trả lời. Vui lòng thử lại sau."

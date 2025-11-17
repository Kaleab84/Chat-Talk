from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import logging
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)
# Handles chat questions by retrieving RAG context and calling Gemini.
router = APIRouter(tags=["chat"])

chat_service = ChatService()

# Gemini model details
GEMINI_API_KEY = "AIzaSyCFVJzYUPJUl-o3vy-n3Yiq2OpeChtCNZY"
GEMINI_MODEL = "models/gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"


SUPABASE_PUBLIC_URL = "https://uqdnuaxbhafstditsmfd.supabase.co/storage/v1/object/public/cfc-docs/"


class ChatRequest(BaseModel):
    message: str
    top_k: int = 3



class ChatResponse(BaseModel):
    success: bool
    message: str
    paragraph: str
    bullets: list[str]
    images: list[str] = [] 


# Chat endpoint
@router.post("/chat", response_model=ChatResponse)

async def chat_with_bot(request: ChatRequest):
    try:
        # Retrieve context from vector store    
        results = chat_service.search_documents(request.message, request.top_k).get("results", [])

        # Initialize lists for context text and image URLs
        context_texts = []
        image_urls = []

        # Iterate through search results
        for r in results:
            # Add text from current result to context text list
            context_texts.append(r.get("text", ""))

            # If this chunk has images convert paths to public URLs
            for img_path in r.get("image_paths", []):
                image_urls.append(SUPABASE_PUBLIC_URL + img_path)

        combined_context = "\n".join(context_texts) if context_texts else "No relevant context found."

        # Create prompt for Gemini model
        prompt = f"""
        You are an assistant supporting users of animal feed management software.
        Base your answer ONLY on the provided context.

        Context:
        {combined_context}

        Relevant Images (if useful for explanation):
        {chr(10).join(image_urls) if image_urls else "No images available."}

        # User question
        User Question:
        {request.message}

        Respond in this format:
        1) One short clear explanatory paragraph.
        2) Then list 3 key takeaways as bullet points.
        If images matter, say: "See reference image below."
        """

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
         # Call Gemini API to generate response
        response = requests.post(GEMINI_URL, json=payload)
        # Check if response is successful
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Gemini API Error → {response.text}")

        data = response.json()
        full_text = data["candidates"][0]["content"]["parts"][0]["text"]

        # --- Step 3: Format Gemini output ---
        lines = full_text.split("\n")
        paragraph = lines[0].strip()
        bullets = [l.strip("-• ").strip() for l in lines[1:] if l.strip()][0:3]

        # Return text + images
        return ChatResponse(
            success=True,
            message=request.message,
            paragraph=paragraph,
            bullets=bullets,
            images=image_urls  # Frontend can now display them
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from typing import List, Dict, Any, Optional
import logging
import re
import random
from pathlib import Path
from app.core.rag import RAGPipeline
from app.core.vector_store import VectorStore
from app.core.embeddings import EmbeddingModel
from app.services.document_processor import DocumentProcessor
from app.config import settings

logger = logging.getLogger(__name__)

class ChatService:
    """Main service for chatbot interactions."""
    
    def __init__(self):
        self.rag_pipeline = RAGPipeline()
        self.vector_store = VectorStore()
        self.embedding_model = EmbeddingModel()
        self.document_processor = DocumentProcessor()
        # Track last canned replies to avoid repeating verbatim
        self._last_small_talk_reply: Optional[str] = None
        self._last_capability_reply: Optional[str] = None
        self._sent_small_talk_greeting: bool = False
    
    def search_documents(self, query: str, top_k: int = None) -> Dict[str, Any]:
        """Search for relevant document chunks."""
        try:
            if top_k is None:
                top_k = settings.DEFAULT_TOP_K
            
            # Check if vector store has any data
            if self._is_vector_store_empty():
                return {
                    "success": False,
                    "query": query,
                    "results": [],
                    "total_results": 0,
                    "error": "I'm sorry. I don't seem to have the right knowledge to help with that right now."
                }
            
            context_chunks = self.rag_pipeline.retrieve_context(query, top_k)
            
            if not context_chunks:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "total_results": 0,
                    "message": "I don't seem to have much knowledge regarding that topic. Maybe try a different phrase or topic, and I'll help where I can."
                }
            
            return {
                "success": True,
                "query": query,
                "results": context_chunks,
                "total_results": len(context_chunks)
            }
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }
    
    def ask_question(self, question: str, top_k: int = None) -> Dict[str, Any]:
        """Get context-aware response to a question."""
        try:
            if top_k is None:
                top_k = settings.DEFAULT_TOP_K
            
            # Lightly handle greetings/small talk without requiring context
            if self._is_small_talk(question):
                if not self._sent_small_talk_greeting:
                    reply = self._small_talk_reply()
                    self._sent_small_talk_greeting = True
                    return {
                        "success": True,
                        "question": question,
                        "answer": reply,
                        "context_used": [],
                        "confidence": 0.0,
                    }
                # Already greeted once; proceed with normal answer generation
            
            # Handle capability/meta prompts without strict context
            if self._is_capability_prompt(question):
                return {
                    "success": True,
                    "question": question,
                    "answer": self._capability_reply(),
                    "context_used": [],
                    "confidence": 0.0,
                }
            
            # Check if vector store has any data
            if self._is_vector_store_empty():
                return {
                    "success": False,
                    "question": question,
                    "answer": "I'd love to help, but I don't have enough knowledge yet.",
                    "context_used": [],
                    "confidence": 0.0,
                    "error": "empty_vector_store"
                }
            
            # Retrieve relevant context
            context_chunks = self.rag_pipeline.retrieve_context(question, top_k)
            
            if not context_chunks:
                return {
                    "success": True,
                    "question": question,
                    "answer": "I don't seem to know anything about that yet. If you could rephrase the question or point me toward a specific topic, I'll happily help where I can.",
                    "context_used": [],
                    "confidence": 0.0
                }
            
            # Format context
            formatted_context = self.rag_pipeline.format_context(context_chunks)

            # Prefer Gemini if configured, otherwise OpenAI, otherwise a simple stub
            if getattr(settings, "GEMINI_API_KEY", None):
                try:
                    answer = self._generate_gemini_answer(question, formatted_context)
                except Exception as gem_exc:
                    logger.warning(f"Gemini generation failed, falling back: {gem_exc}")
                    if getattr(settings, "OPENAI_API_KEY", None):
                        try:
                            answer = self._generate_gpt_answer(question, formatted_context)
                        except Exception as gpt_exc:
                            logger.warning(f"OpenAI generation also failed, using stub: {gpt_exc}")
                            answer = self._generate_simple_answer(question, context_chunks, formatted_context)
                    else:
                        answer = self._generate_simple_answer(question, context_chunks, formatted_context)
            elif getattr(settings, "OPENAI_API_KEY", None):
                try:
                    answer = self._generate_gpt_answer(question, formatted_context)
                except Exception as gpt_exc:
                    logger.warning(f"OpenAI generation failed, using stub: {gpt_exc}")
                    answer = self._generate_simple_answer(question, context_chunks, formatted_context)
            else:
                answer = self._generate_simple_answer(question, context_chunks, formatted_context)

            return {
                "success": True,
                "question": question,
                "answer": answer,
                "context_used": context_chunks,
                "confidence": self._calculate_confidence(context_chunks)
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "answer": None
            }

    def ask_question_with_images(self, question: str, images: List[Dict[str, Any]], top_k: int = None) -> Dict[str, Any]:
        """Get context-aware response and include user images in the generation step.

        Images are used as additional signals for the LLM (not indexed).
        """
        try:
            if top_k is None:
                top_k = settings.DEFAULT_TOP_K

            if self._is_small_talk(question):
                return {
                    "success": True,
                    "question": question,
                    "answer": self._small_talk_reply(),
                    "context_used": [],
                    "confidence": 0.0,
                }

            if self._is_capability_prompt(question):
                return {
                    "success": True,
                    "question": question,
                    "answer": self._capability_reply(),
                    "context_used": [],
                    "confidence": 0.0,
                }

            # Retrieve context
            context_chunks = self.rag_pipeline.retrieve_context(question, top_k)
            formatted_context = self.rag_pipeline.format_context(context_chunks)

            # Prefer Gemini multimodal if configured; else fall back
            if getattr(settings, "GEMINI_API_KEY", None):
                try:
                    answer = self._generate_gemini_answer_with_images(question, formatted_context, images)
                except Exception as gem_exc:
                    logger.warning(f"Gemini multimodal failed, falling back: {gem_exc}")
                    answer = self._generate_simple_answer(question, context_chunks, formatted_context)
            elif getattr(settings, "OPENAI_API_KEY", None):
                # OpenAI path currently ignores images unless a vision model is configured.
                try:
                    answer = self._generate_gpt_answer(question, formatted_context)
                except Exception as gpt_exc:
                    logger.warning(f"OpenAI generation failed, using stub: {gpt_exc}")
                    answer = self._generate_simple_answer(question, context_chunks, formatted_context)
            else:
                answer = self._generate_simple_answer(question, context_chunks, formatted_context)

            return {
                "success": True,
                "question": question,
                "answer": answer,
                "context_used": context_chunks,
                "confidence": self._calculate_confidence(context_chunks),
            }
        except Exception as e:
            logger.error(f"Error answering question with images: {e}")
            return {
                "success": False,
                "error": str(e),
                "question": question,
                "answer": None,
            }
    
    def _generate_simple_answer(self, question: str, context_chunks: List[Dict[str, Any]], formatted_context: str) -> str:
        """Generate a simple answer from context (placeholder for GPT integration)."""
        # This is a placeholder implementation
        # In the full version, this would integrate with OpenAI GPT
        
        if not context_chunks:
            return "No relevant information found."
        
        # Return the most relevant chunk with some formatting
        best_match = context_chunks[0]
        answer = f"Based on the documentation, here's what I found:\n\n"
        answer += f"{best_match['text'][:500]}..."
        
        if len(context_chunks) > 1:
            answer += f"\n\nAdditional relevant information is available from {len(context_chunks) - 1} other sources."
        
        return answer

    def _generate_gpt_answer(self, question: str, formatted_context: str) -> str:
        """Use OpenAI Chat Completions to generate a grounded answer from context."""
        # Lazy import to avoid hard dependency if key is unset
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"OpenAI SDK not available: {exc}")

        client = OpenAI()

        system_prompt = (
            "You are a helpful assistant. Answer using only accurate information you have access to. "
            "Do not mention â€˜context windowsâ€™, â€˜retrievalâ€™, or how you obtained information; answer directly. "
            "When information is missing, ask one brief clarifying question or state what is missing in one sentence. "
            "Do not use conditional 'if â€¦ then â€¦' phrasing; avoid starting sentences with 'If'. "
            "For greetings or general chit-chat, respond naturally and guide the user toward a specific question. "
            "Keep answers concise (1â€“3 sentences) and avoid repeating guidance across messages."
        )
        resp = client.chat.completions.create(
            model=getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": system_prompt},
                # Provide reference material without labels to avoid echoes
                {"role": "system", "content": formatted_context},
                {"role": "user", "content": question},
            ],
            temperature=0.4,
            max_tokens=500,
        )

        content = resp.choices[0].message.content if resp and resp.choices else None
        if not content:
            raise RuntimeError("Empty response from OpenAI")
        return content.strip()

    def _generate_gemini_answer(self, question: str, formatted_context: str) -> str:
        """Use Google Gemini to generate a grounded answer from context."""
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Google Generative AI SDK not available: {exc}")

        if not getattr(settings, "GEMINI_API_KEY", None):
            raise RuntimeError("GEMINI_API_KEY is not configured")

        # Configure client
        genai.configure(api_key=settings.GEMINI_API_KEY)

        system_prompt = (
            "You are a helpful assistant. Answer using only accurate information you have access to. "
            "Do not mention â€˜context windowsâ€™, â€˜retrievalâ€™, or how you obtained information; answer directly. "
            "When information is missing, ask one brief clarifying question or state what is missing in one sentence. "
            "Do not use conditional 'if â€¦ then â€¦' phrasing; avoid starting sentences with 'If'. "
            "For greetings or general chit-chat, respond naturally and guide the user toward a specific question. "
            "Keep answers concise (1â€“3 sentences) and avoid repeating guidance across messages."
        )
        model_name = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)

        # Provide reference text as a separate part without a label to reduce echoes
        # Add light variation to avoid identical phrasing across conversations
        temp = random.uniform(0.3, 0.7)
        resp = model.generate_content(
            [system_prompt, formatted_context, f"Question:\n{question}\n\nAnswer:"],
            generation_config={
                "temperature": temp,
                "top_p": 0.9,
                "max_output_tokens": 500,
            },
        )
        content = getattr(resp, "text", None)
        if not content:
            # Some responses may be structured; attempt to extract from candidates
            try:
                if resp and getattr(resp, "candidates", None):
                    parts = resp.candidates[0].content.parts
                    content = "".join([getattr(p, "text", "") for p in parts])
            except Exception:
                pass
        if not content:
            raise RuntimeError("Empty response from Gemini")
        return content.strip()

    def _generate_gemini_answer_with_images(self, question: str, formatted_context: str, images: List[Dict[str, Any]]) -> str:
        """Use Gemini multimodal generation with user-provided images plus RAG context."""
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Google Generative AI SDK not available: {exc}")

        if not getattr(settings, "GEMINI_API_KEY", None):
            raise RuntimeError("GEMINI_API_KEY is not configured")

        genai.configure(api_key=settings.GEMINI_API_KEY)

        system_prompt = (
            "You are a helpful assistant. Answer using only accurate information you have access to. "
            "Do not mention â€˜context windowsâ€™, â€˜retrievalâ€™, or how you obtained information; answer directly. "
            "When information is missing, ask one brief clarifying question or state what is missing in one sentence. "
            "Do not use conditional 'if â€¦ then â€¦' phrasing; avoid starting sentences with 'If'. "
            "Consider the attached images as part of the userâ€™s question. "
            "Keep answers concise (1â€“3 sentences) and avoid repeating guidance across messages."
        )
        model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        model = genai.GenerativeModel(model_name)

        # Build content parts: system -> images -> reference text -> question
        parts: List[Any] = [system_prompt]
        for img in images or []:
            try:
                parts.append({"mime_type": img.get("content_type", "image/png"), "data": img["data"]})
            except Exception:
                continue
        parts.append(formatted_context)
        parts.append(f"Question:\n{question}\n\nAnswer:")

        temp = random.uniform(0.3, 0.7)
        resp = model.generate_content(
            parts,
            generation_config={
                "temperature": temp,
                "top_p": 0.9,
                "max_output_tokens": 500,
            },
        )

        content = getattr(resp, "text", None)
        if not content:
            try:
                if resp and getattr(resp, "candidates", None):
                    parts_out = resp.candidates[0].content.parts
                    content = "".join([getattr(p, "text", "") for p in parts_out])
            except Exception:
                pass
        if not content:
            raise RuntimeError("Empty response from Gemini (multimodal)")
        return content.strip()

    def _is_small_talk(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return True
        # Word-boundary match to avoid catching "you" as "yo"
        patterns = [
            r"\bhi\b",
            r"\bhello\b",
            r"\bhey\b",
            r"\bgood\s+(morning|afternoon|evening)\b",
            r"\bwhat'?s\s+up\b",
            r"\bhow\s+are\s+you\b",
            r"\bare\s+you\s+there\b",
            r"\bi\s+have\s+a\s+question\b",
            r"\bcan\s+i\s+ask\s+a\s+question\b",
        ]
        return any(re.search(p, t) for p in patterns)

    def _small_talk_reply(self) -> str:
        # Summarize ingested corpus (best-effort; safe if folders missing)
        doc_root = getattr(settings, "LOCAL_CONTENT_ROOT", None)
        doc_names: List[str] = []
        doc_count = 0
        try:
            if doc_root:
                p = Path(doc_root)
                if p.exists() and p.is_dir():
                    dirs = [d for d in p.iterdir() if d.is_dir()]
                    doc_count = len(dirs)
                    doc_names = [d.name for d in dirs[:3]]
        except Exception:
            pass

        greetings = [
            "Hi, there! How can I help you today?",
            "Hey, there! What can I do for you?",
            "Hey! Thanks for reaching out. What can I help with?",
            "Hi! What can I help you with?",
            "Hey! I'm here to help. Just let me know what you're working on.",
        ]

        random.shuffle(greetings)
        reply_choice = greetings[0]
        if self._last_small_talk_reply:
            for opt in greetings:
                if opt != self._last_small_talk_reply:
                    reply_choice = opt
                    break
        self._last_small_talk_reply = reply_choice
        return reply_choice

    def _is_capability_prompt(self, text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        patterns = [
            r"\bwhat\s+do\s+you\s+know\b",
            r"\bwhat\s+can\s+you\s+do\b",
            r"\bhow\s+can\s+you\s+help\b",
            r"\bwhat\s+are\s+you\b",
        ]
        return any(re.search(p, t) for p in patterns)

    def _capability_reply(self) -> str:
        # Brief, non-repetitive capabilities overview with corpus hint
        doc_root = getattr(settings, "LOCAL_CONTENT_ROOT", None)
        doc_count = 0
        try:
            if doc_root:
                p = Path(doc_root)
                if p.exists() and p.is_dir():
                    doc_count = len([d for d in p.iterdir() if d.is_dir()])
        except Exception:
            pass

        corpus_blurb = ""
        if doc_count:
            corpus_blurb = f" I currently have {doc_count} document collections I can reference."
        templates = [
            "I'm here to answer questions about CFC software using trustworthy internal information.{corpus} Tell me what you're working on and I'll share the most helpful details I can find.",
            "I can explore your CFC documentation and highlight the parts that matter.{corpus} Ask about a process, a definition, or where to find something and I'll walk you through it.",
            "Think of me as your friendly product assistant: I search the knowledge base and provide concise explanations.{corpus} Feel free to mention any screenshots or error messages if that helps.",
        ]
        random.shuffle(templates)
        reply = templates[0].format(corpus=corpus_blurb)
        if self._last_capability_reply:
            for t in templates:
                candidate = t.format(corpus=corpus_blurb)
                if candidate != self._last_capability_reply:
                    reply = candidate
                    break
        self._last_capability_reply = reply
        return reply
    
    def _calculate_confidence(self, context_chunks: List[Dict[str, Any]]) -> float:
        """Calculate confidence score based on context quality."""
        if not context_chunks:
            return 0.0
        
        # Simple confidence calculation based on top match score
        top_score = context_chunks[0].get('score', 0.0)
        
        # Normalize score to 0-1 range (assuming Pinecone cosine similarity)
        confidence = max(0.0, min(1.0, top_score))
        
        return round(confidence, 3)
    
    def get_recommendations(self, query: str, content_type: str = "all") -> Dict[str, Any]:
        """Get content recommendations based on query."""
        try:
            # Search for relevant content
            search_result = self.search_documents(query, top_k=10)
            
            if not search_result["success"]:
                return search_result
            
            # Group by source and content type
            recommendations = {
                "documents": [],
                "videos": [],
                "related_topics": []
            }
            
            for result in search_result["results"]:
                source_type = result.get("source_type", "document")
                
                rec_item = {
                    "title": result.get("source"),
                    "relevance_score": result.get("score"),
                    "preview": (result.get("text") or "")[:200] + "...",
                    "source_type": source_type,
                    "doc_id": result.get("doc_id"),
                    "section_id": result.get("section_id"),
                    "section_path": result.get("section_path"),
                    "section_title": result.get("section_title"),
                    "image_paths": result.get("image_paths", []),
                }
                
                if source_type == "video":
                    recommendations["videos"].append(rec_item)
                else:
                    recommendations["documents"].append(rec_item)
            
            # Remove duplicates and sort by relevance
            recommendations["documents"] = self._deduplicate_recommendations(recommendations["documents"])
            recommendations["videos"] = self._deduplicate_recommendations(recommendations["videos"])
            
            return {
                "success": True,
                "query": query,
                "recommendations": recommendations,
                "total_items": len(recommendations["documents"]) + len(recommendations["videos"])
            }
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "recommendations": {"documents": [], "videos": [], "related_topics": []}
            }
    
    def _is_vector_store_empty(self) -> bool:
        """Return True when the vector store has no stored vectors."""
        try:
            stats = self.vector_store.get_index_stats()
        except AttributeError:
            logger.warning("VectorStore is missing get_index_stats(); skipping empty-store check.")
            return False
        except Exception as e:
            logger.warning(f"Could not check vector store stats: {e}")
            return False

        total_vectors = stats.get("total_vector_count")
        if total_vectors is None:
            namespaces = stats.get("namespaces") or {}
            total_vectors = sum(ns.get("vectorCount", 0) for ns in namespaces.values())

        return total_vectors == 0

    def _deduplicate_recommendations(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate recommendations based on title."""
        seen_titles = set()
        unique_items = []
        
        for item in sorted(items, key=lambda x: x["relevance_score"], reverse=True):
            if item["title"] not in seen_titles:
                seen_titles.add(item["title"])
                unique_items.append(item)
        
        return unique_items[:5]  # Limit to top 5







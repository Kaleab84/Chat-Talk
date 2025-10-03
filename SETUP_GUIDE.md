# CFC Chatbot - Setup and Usage Guide

## 📋 Prerequisites

- **Python 3.10+** (You have Python 3.12.6 ✅)
- **Pinecone API Key** (Already configured in your code ✅)
- **Internet connection** for downloading models and connecting to Pinecone

## 🚀 Quick Start

### 1. Install Dependencies
All required packages have been installed in your virtual environment:
```bash
# The following packages are now installed:
- fastapi
- uvicorn[standard]
- pydantic
- pinecone
- sentence-transformers
- python-docx
- numpy
```

### 2. Run the Application
```bash
# Navigate to your project directory
cd "C:\Users\nifta\Documents\GitHub\Chat-Talk"

# Run the FastAPI server
C:/Users/nifta/Documents/GitHub/Chat-Talk/.venv/Scripts/python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Alternative shorter command:
```bash
# Activate virtual environment first
.\.venv\Scripts\activate

# Then run with simpler command
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access the Application
- **API Base URL**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## 🔧 API Endpoints

### 1. Health Check
```http
GET /
```
**Response**: `{"ok": true, "message": "CFC Chatbot API running"}`

### 2. Ingest Documents
```http
POST /ingest
```
**Purpose**: Process and store document content in Pinecone vector database

**Request Body**:
```json
{
  "filename": "sample_guide.docx"  // Optional, defaults to "sample_guide.docx"
}
```

**Response**:
```json
{
  "ok": true,
  "source": "/path/to/file",
  "num_chunks": 25,
  "example_chunk": "First 240 characters of first chunk..."
}
```

### 3. Search Documents
```http
POST /search
```
**Purpose**: Find relevant document chunks based on query

**Request Body**:
```json
{
  "query": "installation process",
  "top_k": 5  // Optional, defaults to 5
}
```

**Response**:
```json
{
  "ok": true,
  "results": [
    {
      "rank": 1,
      "score": 0.85,
      "text": "Relevant document chunk text...",
      "source": "sample_guide.docx"
    }
  ]
}
```

### 4. Ask Questions
```http
POST /ask
```
**Purpose**: Get context-aware answers to questions

**Request Body**:
```json
{
  "question": "How do I install the software?",
  "top_k": 4  // Optional, defaults to 4
}
```

**Response**:
```json
{
  "ok": true,
  "question": "How do I install the software?",
  "context_snippets": [...],
  "answer_stub": "First 1200 characters of combined context..."
}
```

## 📁 Document Requirements

Your documents should be:
- **Format**: `.docx` files
- **Location**: `data/` folder in your project
- **Content**: Well-structured text content

**Available Documents**:
- `sample_guide.docx` ✅
- `rationew_guide.docx` ✅
- `ratio_guide.DOC` ✅
- `C5 Reinstallation Tutorial.doc` (Note: .doc format, may need conversion)
- `AgrisCostImport (1).doc` (Note: .doc format, may need conversion)

## 🔧 Configuration

### Pinecone Settings
- **Index Name**: `cfc-chatbot`
- **Dimension**: 384 (matches all-MiniLM-L6-v2 model)
- **Metric**: cosine
- **Cloud**: AWS
- **Region**: us-east-1

### Model Settings
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Chunk Size**: 600 characters
- **Chunk Overlap**: 120 characters

## 🛠️ Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Use a different port
   uvicorn main:app --reload --port 8001
   ```

2. **Pinecone Connection Issues**
   - Verify your API key is correct
   - Check internet connection
   - Ensure Pinecone service is available

3. **Document Processing Errors**
   - Ensure .docx files are not corrupted
   - Check file permissions
   - Convert .doc files to .docx format if needed

4. **Model Download Issues**
   - First run may take time to download sentence-transformers model
   - Ensure stable internet connection

## 📝 Example Usage Workflow

1. **Start the server**:
   ```bash
   uvicorn main:app --reload
   ```

2. **Ingest a document**:
   ```bash
   curl -X POST "http://localhost:8000/ingest" \
     -H "Content-Type: application/json" \
     -d '{"filename": "sample_guide.docx"}'
   ```

3. **Search for information**:
   ```bash
   curl -X POST "http://localhost:8000/search" \
     -H "Content-Type: application/json" \
     -d '{"query": "installation steps", "top_k": 3}'
   ```

4. **Ask a question**:
   ```bash
   curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What are the system requirements?"}'
   ```

## 🚀 Next Steps

1. **Ingest your documents** using the `/ingest` endpoint
2. **Test the search** functionality with sample queries
3. **Build a frontend** to interact with your chatbot
4. **Add authentication** if needed for production use
5. **Monitor usage** and optimize chunk sizes based on your documents

Your CFC Chatbot API is now ready to use! 🎉
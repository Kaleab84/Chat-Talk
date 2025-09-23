This is a backend API for an AI-powered chatbot built with FastAPI. The chatbot retrieves information from documents and provides semantic search + GPT-based responses.

Quick Start

Clone the repo

git clone https://github.com/Kaleab84/your-repo-name.git
cd your-repo-name


Create & activate virtual environment

python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Mac/Linux


Install dependencies

pip install -r requirements.txt


Run the server

uvicorn main:app --reload


Visit  http://127.0.0.1:8000/docs
 to test the API.

Project Structure
data/         # Documents & datasets
main.py       # FastAPI entry point
.gitignore    # Ignored files (e.g., .venv, cache)


Add authentication & user login

Connect to a database for persistent storage

Build a document ingestion pipeline

Implement semantic search with embeddings

Integrate GPT-based responses

Add unit tests & CI/CD pipeline

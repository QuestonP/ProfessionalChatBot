from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_ollama.llms import OllamaLLM
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from contextlib import asynccontextmanager
import os
import shutil
import uvicorn

# ===== Global vars =====
model = None
vectorstore = None
retriever = None
chain = None
profile_file_path = "./data/professional_profile.txt"
db_loc = "./vector_db"

# ===== Utility Functions =====
def clear_vector_db():
    """Delete the entire vector database folder if it exists."""
    if os.path.exists(db_loc):
        print("🗑️ Clearing existing vector database...")
        shutil.rmtree(db_loc)

def load_documents(filepath: str):
    """Load and split documents from profile file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError("Profile file not found at ./data/professional_profile.txt")

    with open(filepath, "r", encoding="utf-8") as file:
        content = file.read()

    sections = content.split("---")
    documents = []
    for section in sections:
        section = section.strip()
        if section:
            lines = section.split("\n", 1)
            title = lines[0].strip().rstrip(":")
            content_text = lines[1].strip() if len(lines) > 1 else section
            documents.append(
                Document(page_content=content_text, metadata={"title": title})
            )
    return documents

def rebuild_vectorstore(embeddings):
    """Completely rebuild the vector store from scratch."""
    global vectorstore, retriever

    print("🔄 Rebuilding vector database from professional_profile.txt...")
    clear_vector_db()

    # Load documents and build the DB
    documents = load_documents(profile_file_path)
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=db_loc,
    )

    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    print("✅ Vector database rebuilt successfully.")

# ===== Pydantic Models =====
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    retrieved_docs: list
    status: str

# ===== Lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, vectorstore, retriever, chain

    print("🚀 Starting RAG API server...")

    # Initialize LLM & embeddings
    model = OllamaLLM(model="gemma3:1b")
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Always rebuild vector DB from scratch on startup
    rebuild_vectorstore(embeddings)

    # Prompt chain
    template = """
        You are a professional chatbot representing Quest Parker.
        Use ONLY the provided context to answer questions about Quest Parker.
        If the context is not relevant, answer using general knowledge.
        Cite the context titles in your answer when possible.

        Context:
        {context}

        Question: {question}
        """
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model

    yield
    print("🛑 Shutting down RAG API server...")

# ===== FastAPI App =====
app = FastAPI(title="Quest Parker Chatbot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Static files (only for production) =====
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        return FileResponse("frontend/dist/index.html")

@app.get("/")
async def root():
    return {"message": "Quest Parker Chatbot API", "status": "running"}

# ===== Chat Endpoint =====
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        global retriever

        # Smart detection: check if question is related to Quest Parker
        keywords = ["quest", "parker", "his work", "background", "career", "experience", "projects", "skills", "education", "bio", "about him"]
        lower_question = request.question.lower()

        use_retrieval = any(keyword in lower_question for keyword in keywords)

        if use_retrieval:
            print("📖 Retrieval mode ON: Fetching relevant context...")
            relevant_docs = retriever.get_relevant_documents(request.question)
        else:
            print("⚡ Retrieval mode OFF: Answering directly...")
            relevant_docs = []

        # Build context
        context = "\n\n".join(
            [f"{doc.metadata.get('title')}: {doc.page_content}" for doc in relevant_docs]
        ) if relevant_docs else "No context needed."

        result = chain.invoke({"context": context, "question": request.question})

        doc_info = [
            {
                "title": doc.metadata.get("title", ""),
                "content_preview": doc.page_content[:100] + "..."
            }
            for doc in relevant_docs
        ]

        return ChatResponse(answer=result, retrieved_docs=doc_info, status="success")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

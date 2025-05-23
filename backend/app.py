from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_service import RAGService
from memory_manager import MemoryManager
from typing import List

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_service = RAGService()
memory_manager = MemoryManager()

class QuestionRequest(BaseModel):
    question: str
    conversation_id: str = "default"

class AnswerResponse(BaseModel):
    answer: str
    conversation_id: str

class URLRequest(BaseModel):
    urls: List[str]
    include_internal: bool = False

@app.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    try:
        # Get RAG chain
        rag_chain = rag_service.get_rag_chain()
        
        # Add to conversation history
        memory_manager.add_message(
            request.conversation_id, 
            "user", 
            request.question
        )
        
        # Get prompt with memory
        prompt_with_memory = memory_manager.get_rag_prompt_with_memory(
            request.conversation_id,
            request.question
        )
        
        # Get answer
        answer = rag_chain.invoke(prompt_with_memory)
        
        # Add assistant response to history
        memory_manager.add_message(
            request.conversation_id, 
            "assistant", 
            answer
        )
        
        return AnswerResponse(
            answer=answer,
            conversation_id=request.conversation_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/load_urls")
async def load_urls(request: URLRequest):
    try:
        rag_service.load_from_urls(request.urls, request.include_internal)
        return {"message": f"Successfully loaded {len(request.urls)} URLs"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):
    history = memory_manager.get_conversation_history(conversation_id)
    return {"conversation": history}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
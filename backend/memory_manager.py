from typing import Dict, List
from pydantic import BaseModel

class Conversation(BaseModel):
    conversation_id: str
    messages: List[Dict[str, str]]

class MemoryManager:
    def __init__(self):
        self.conversations: Dict[str, Conversation] = {}
    
    def create_conversation(self, conversation_id: str) -> Conversation:
        conversation = Conversation(
            conversation_id=conversation_id,
            messages=[]
        )
        self.conversations[conversation_id] = conversation
        return conversation
    
    def add_message(self, conversation_id: str, role: str, content: str):
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)
        
        self.conversations[conversation_id].messages.append({
            "role": role,
            "content": content
        })
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        if conversation_id in self.conversations:
            return self.conversations[conversation_id].messages
        return []
    
    def get_rag_prompt_with_memory(self, conversation_id: str, question: str) -> str:
        history = self.get_conversation_history(conversation_id)
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
        
        prompt = f"""Previous conversation:
        {history_text}
        
        New question: {question}
        
        Answer in a friendly and helpful manner:"""
        
        return prompt
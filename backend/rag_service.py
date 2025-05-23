from langchain_unstructured import UnstructuredLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from web_scraper import WebScraper
from typing import List
import tempfile
import os
import unicodedata

class RAGService:
    def __init__(self):
        self.vectorstore = None
        self.retriever = None
        self.llm = None
        self.scraper = WebScraper(max_internal_links=3)
        self.initialize_llm()
    
    def initialize_llm(self):
        """Initialize the LLM model"""
        self.llm = ChatOllama(model='llama2', temperature=0.7)
    
    def load_from_urls(self, urls: List[str], include_internal: bool = False):
        """
        Load and process content from given URLs
        
        Args:
            urls: List of URLs to scrape
            include_internal: Whether to follow internal links
        """
        # Scrape content from URLs
        scraped_content = self.scraper.scrape_multiple_urls(urls, include_internal)
        
        # Normalize unicode characters
        normalized_content = unicodedata.normalize('NFKC', scraped_content)
        
        # Save to temporary HTML file with explicit UTF-8 encoding
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.html', 
            delete=False, 
            encoding='utf-8'
        ) as f:
            f.write(normalized_content)
            temp_path = f.name
        
        try:
            # Load documents with error handling
            loader = UnstructuredLoader(file_path=temp_path)
            docs = []
            for doc in loader.lazy_load():
                docs.append(doc)
            
            if not docs:
                raise ValueError("No documents could be loaded from the provided URLs")
            
            # Splitting Data with overlap for context
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
                length_function=len,
                is_separator_regex=False,
            )
            splits = text_splitter.split_documents(docs)
            
            # Initialize embeddings with HuggingFace model
            modelPath = "sentence-transformers/all-MiniLM-l6-v2"
            model_kwargs = {'device':'cpu'}
            encode_kwargs = {'normalize_embeddings': False}
            
            embeddings = HuggingFaceEmbeddings(
                model_name=modelPath,    
                model_kwargs=model_kwargs, 
                encode_kwargs=encode_kwargs 
            )
            
            # Create vectorstore and retriever
            self.vectorstore = FAISS.from_documents(splits, embeddings)
            self.retriever = self.vectorstore.as_retriever(
                search_type="mmr",  # Maximal Marginal Relevance
                search_kwargs={'k': 4, 'fetch_k': 10}
            )
            
        except Exception as e:
            # Clean up and re-raise the exception
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise RuntimeError(f"Error processing documents: {str(e)}")
        
        finally:
            # Ensure temporary file is cleaned up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def get_rag_chain(self):
        """
        Create and return the RAG chain with memory and context
        
        Returns:
            A configured RAG chain ready for invocation
        """
        template = """You are a friendly and helpful Knowledge Assistant called "K-Bot". 
        Use the following pieces of context to answer the question at the end. 
        If you don't know the answer, just say that you don't know, don't try to make up an answer.
        Keep the answer concise but friendly and helpful.
        
        Context: {context}
        
        Question: {question}
        
        Helpful Answer:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        def format_docs(docs):
            """Format documents for context injection"""
            return "\n\n".join(doc.page_content for doc in docs)
        
        # Create the RAG pipeline
        rag_chain = (
            {"context": self.retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        return rag_chain
    
    def is_ready(self) -> bool:
        """
        Check if the RAG service is ready to answer questions
        
        Returns:
            bool: True if vectorstore and retriever are initialized
        """
        return self.vectorstore is not None and self.retriever is not None
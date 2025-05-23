import streamlit as st
import requests
import uuid
from datetime import datetime

# Backend API configuration
BACKEND_URL = "http://localhost:8000"

# Initialize session state
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "urls_loaded" not in st.session_state:
    st.session_state.urls_loaded = False
if "show_url_input" not in st.session_state:
    st.session_state.show_url_input = True

# Page configuration
st.set_page_config(
    page_title="Knowledge Assistant",
    page_icon="🤖",
    layout="centered"
)

# Sidebar for configuration
with st.sidebar:
    st.title("Configuration")
    
    if st.session_state.show_url_input:
        with st.form("url_form"):
            st.subheader("Teach Me Websites")
            urls = st.text_area(
                "Enter website URLs (one per line)",
                placeholder="https://example.com\nhttps://another-site.org",
                help="I'll analyze these websites to answer your questions"
            )
            include_internal = st.checkbox(
                "Include internal links",
                value=False,
                help="I'll follow links within these websites"
            )
            submit_urls = st.form_submit_button("Teach Me")
        
        if submit_urls:
            url_list = [url.strip() for url in urls.split('\n') if url.strip()]
            if url_list:
                try:
                    with st.spinner("Reading websites..."):
                        response = requests.post(
                            f"{BACKEND_URL}/load_urls",
                            json={
                                "urls": url_list,
                                "include_internal": include_internal
                            }
                        )
                    
                    if response.status_code == 200:
                        st.session_state.urls_loaded = True
                        st.session_state.show_url_input = False
                        st.success("I've learned from these websites! Ask me anything.")
                        st.rerun()
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Failed to load URLs')}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
            else:
                st.warning("Please enter at least one valid URL")

    st.divider()
    st.subheader("Conversation")
    if st.button("New Conversation"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.urls_loaded = False
        st.session_state.show_url_input = True
        st.rerun()
    
    st.write(f"Conversation ID: `{st.session_state.conversation_id}`")
    st.caption(f"Started at {datetime.now().strftime('%H:%M:%S')}")

# Main chat interface
st.title("Knowledge Assistant 🤖")

# Initial greeting
if len(st.session_state.messages) == 0:
    st.info("""
    Hi there! I'm your Knowledge Assistant. 
    
    To get started:
    1. Enter website URLs in the sidebar
    2. I'll analyze the content
    3. Ask me anything about those websites!
    """)
    st.session_state.messages.append({"role": "assistant", "content": "Ready to learn from websites you provide!"})

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Type your question here..."):
    if not st.session_state.urls_loaded:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Please enter website URLs in the sidebar first so I can learn from them."
        })
        st.rerun()
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get response from backend
    try:
        with st.spinner("Thinking..."):
            response = requests.post(
                f"{BACKEND_URL}/ask",
                json={
                    "question": prompt,
                    "conversation_id": st.session_state.conversation_id
                }
            )
            
            if response.status_code == 200:
                answer = response.json()["answer"]
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                error_msg = response.json().get("detail", "Sorry, I encountered an error.")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_msg}"})
        
        st.rerun()
    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"Connection error: {str(e)}"
        })
        st.rerun()
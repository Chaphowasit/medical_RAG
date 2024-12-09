import streamlit as st
from adaptors.qdrant_adaptors import QdrantAdaptor
from chatbot.chatbot import Chatbot  # Assuming the chatbot implementation is saved in chatbot.py

@st.cache_resource
def get_chatbot():
    """
    Initialize and cache the chatbot instance with a QdrantAdaptor.
    """
    adaptor = QdrantAdaptor()
    adaptor.get_or_create_collection(collection_name="medical")
    return Chatbot(adaptor=adaptor)

# Streamlit UI
st.title("Chatbot with RAG")

# Text input
user_text = st.text_area("Enter your query here:", height=200)

# Submit button
if st.button("Submit"):
    if user_text.strip():
        st.success("Query submitted successfully!")
        st.write("Your query:")
        st.write(user_text)

        # Get the chatbot instance
        chatbot = get_chatbot()

        # Generate a response using the chatbot
        response = chatbot.response(query=user_text)

        # Display the response
        st.write("Chatbot Response:")
        st.write(response)
    else:
        st.error("Please enter a query before submitting.")

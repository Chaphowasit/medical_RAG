import streamlit as st

# from adaptors.qdrant_adaptors import QdrantAdaptor
from chatbot.chatbot import (
    Chatbot,
)


@st.cache_resource
def get_chatbot():
    """
    Initialize and cache the chatbot instance with a QdrantAdaptor.
    """
    # adaptor = QdrantAdaptor()
    return Chatbot(None)


st.title("Chatbot with RAG")


user_text = st.text_area("Enter your query here:", height=200)


if st.button("Submit"):
    if user_text.strip():
        st.success("Query submitted successfully!")
        st.write("Your query:")
        st.write(user_text)

        chatbot = get_chatbot()
        response, rag_response = chatbot.response(query=user_text)

        st.subheader("Chatbot Response:")
        st.write(response)

        st.subheader("RAG Response:")
        st.write(rag_response)

    else:
        st.error("Please enter a query before submitting.")

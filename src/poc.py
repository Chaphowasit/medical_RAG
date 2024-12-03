import streamlit as st
from adaptors.qdrant_adaptors import QdrantAdaptor

@st.cache_resource
def get_qdrant_adaptor():
    adaptor = QdrantAdaptor()
    adaptor.get_or_create_collection(collection_name="medical")
    return adaptor

# Streamlit UI
st.title("RAG search")

# Text input
user_text = st.text_area("Enter your text here:", height=200)

# Submit button
if st.button("Submit"):
    if user_text.strip():
        st.success("Text submitted successfully!")
        st.write("You submitted the following text:")
        st.write(user_text)

        # Use QdrantAdaptor for retrieval
        adaptor = get_qdrant_adaptor()
        results = adaptor.retrieval(query=user_text, top_k=2)
        
        st.write("Similarity Search Results:")
        for rank, result in results.items():
            st.write(f"Rank {rank + 1}:")
            st.write(f"Content: {result['Content']}")
            st.write(f"Metadata: {result['Metadata']}")
    else:
        st.error("Please enter some text before submitting.")

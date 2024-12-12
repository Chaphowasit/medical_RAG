from typing import List
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMListwiseRerank
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_openai import OpenAI
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from qdrant_client import models

# from adaptors.qdrant_adaptors import QdrantAdaptor
# from adaptors.qdrant_adaptors import NLPTransformation
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from dotenv import load_dotenv
import os
from langchain.prompts import PromptTemplate


class Chatbot:
    def __init__(self, adaptor):
        """Initialize the chatbot with Qdrant adaptor and graph."""
        load_dotenv(override=True)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY")
        )
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name="medical",
            embedding=self.embeddings,
        )
        self.llm = OpenAI(temperature=0.5, api_key=os.getenv("OPENAI_API_KEY"))
        self.prompt = PromptTemplate(
            input_variables=["query"],
            template="Rewrite this query to be more specific and useful for a search engine: {query} in thai language",
        )
        # @tool(response_format="content_and_artifact")
        # def retrieve(query: str):
        #     """Retrieve and rerank information related to a query."""

        #     retrieved_docs = self.vector_store.similarity_search(query, k=10)
        #     print("retrieve_docs_len :  ", len(retrieved_docs))

        #     search_results = [
        #         {
        #             "metadata": doc.metadata,
        #             "page_content": doc.page_content,
        #             "keywords": self.nlp_class.extract_keywords(doc.page_content),
        #         }
        #         for doc in retrieved_docs
        #     ]

        #     # reranked_results = self.rerank_documents(query, search_results, top_k=5)

        #     serialized = "\n\n".join(
        #         (f"Source: {doc['metadata']}\n" f"Content: {doc['page_content']}")
        #         for doc in retrieved_docs
        #     )

        #     return serialized, retrieved_docs

        @tool(response_format="content_and_artifact")
        def retrieve(query: str):
            """Retrieve information related to a query."""
            # query = str(self.llm(self.prompt.format(query=query)))
            retriever = self.vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={"score_threshold": 0.5},
            )
            llm = ChatOpenAI(
                model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY")
            )
            _filter = LLMListwiseRerank.from_llm(llm, top_n=10)
            # compressor = LLMChainExtractor.from_llm(llm)
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=_filter, base_retriever=retriever
            )
            compressed_docs = compression_retriever.invoke(query)
            # retrieved_docs = self.vector_store.similarity_search(
            #     query,
            #     k=20,
            #     # filter=models.Filter(
            #     #     should=[
            #     #         models.FieldCondition(
            #     #             key="metadata",
            #     #             match=models.MatchValue(value=query),
            #     #         ),
            #     #     ]
            #     # ),
            # )
            print("retrieve_docs_len : ", len(compressed_docs))
            serialized = "\n\n".join(
                (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
                for doc in compressed_docs
            )
            return serialized, compressed_docs

        set_llm_cache(InMemoryCache())

        # self.adaptor = adaptor
        # self.nlp_class = NLPTransformation()
        self.retrieve = retrieve

        self.llm = ChatOpenAI(model="gpt-4o", max_tokens=8000)

        self.memory = MemorySaver()
        self.graph = self._build_graph(self.memory)
        self.config = {"configurable": {"thread_id": "abc123"}}

    # def rerank_documents(
    #     self, query: str, search_results: List[dict], top_k: int = 5
    # ) -> List[dict]:
    #     """Rerank documents based on keyword overlap with the query."""

    #     query_keywords = self.nlp_class.extract_keywords(query)

    #     def calculate_keyword_match(doc_keywords: List[str]) -> int:
    #         """Counts how many query keywords are in the document's keywords."""
    #         return len(set(query_keywords) & set(doc_keywords))

    #     search_results.sort(
    #         key=lambda x: calculate_keyword_match(x["keywords"]),
    #         reverse=True,
    #     )

    #     return search_results[:top_k]

    def _build_graph(self, memory):
        """Build the chatbot's workflow graph."""

        def query_or_respond(state: MessagesState):
            """Generate tool call for retrieval or respond."""
            llm_with_tools = self.llm.bind_tools([self.retrieve])
            response = llm_with_tools.invoke(state["messages"])

            return {"messages": [response]}

        tools = ToolNode([self.retrieve])

        def generate(state: MessagesState):
            """Generate answer."""
            global DOCSCONTENT
            recent_tool_messages = []
            for message in reversed(state["messages"]):
                if message.type == "tool":
                    recent_tool_messages.append(message)
                else:
                    break
            tool_messages = recent_tool_messages[::-1]

            docs_content = "\n\n".join(doc.content for doc in tool_messages)
            system_message_content = (
                "You are an assistant for question-answering tasks. "
                "Use the following pieces of retrieved context to answer "
                "the question. If the following context don't provide the related answer, "
                "say that you don't know."
                "\n\n"
                f'context: """{docs_content}""" '
            )
            DOCSCONTENT = docs_content
            conversation_messages = [
                message
                for message in state["messages"]
                if message.type in ("human", "system")
                or (message.type == "ai" and not message.tool_calls)
            ]
            prompt = [SystemMessage(system_message_content)] + conversation_messages
            print("prompt msgs:", prompt)
            response = self.llm.invoke(prompt)
            return {"messages": [response]}

        graph_builder = StateGraph(MessagesState)

        graph_builder.add_node(query_or_respond)
        graph_builder.add_node(tools)
        graph_builder.add_node(generate)

        graph_builder.set_entry_point("query_or_respond")
        graph_builder.add_conditional_edges(
            "query_or_respond",
            tools_condition,
            {END: END, "tools": "tools"},
        )
        graph_builder.add_edge("tools", "generate")
        graph_builder.add_edge("generate", END)

        return graph_builder.compile(checkpointer=memory)

    def response(self, query: str):
        """Process a user message through the graph."""
        print("query msgs:", query)
        # final_rag_message = None
        for step in self.graph.stream(
            {"messages": [{"role": "user", "content": query}]},
            stream_mode="values",
            config=self.config,
        ):
            final_message = step["messages"][-1]
            # if len(step["messages"]) > 1:
            #     final_rag_message = step["messages"][-2]
            # print("step : : ", step)
        print("query response:", final_message.content)
        print("=" * 30)
        return final_message.content, DOCSCONTENT

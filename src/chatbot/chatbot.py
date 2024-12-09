from langgraph.graph import MessagesState, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache

from adaptors.qdrant_adaptors import QdrantAdaptor  # Import QdrantAdaptor

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from dotenv import load_dotenv
import os


class Chatbot:
    def __init__(self, adaptor: QdrantAdaptor):
        """Initialize the chatbot with Qdrant adaptor and graph."""
        load_dotenv(override=True)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002", api_key=os.getenv("OPENAI_API_KEY")
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

        @tool(response_format="content_and_artifact")
        def retrieve(query: str):
            """Retrieve information related to a query."""
            retrieved_docs = self.vector_store.similarity_search(query, k=6)
            print(" retrieve_docs_len :  ", len(retrieved_docs))
            serialized = "\n\n".join(
                (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
                for doc in retrieved_docs
            )
            return serialized, retrieved_docs

        # Enable in-memory cache for the chatbot
        set_llm_cache(InMemoryCache())

        self.adaptor = adaptor
        self.retrieve = retrieve

        # Initialize LLM
        self.llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=8000)

        # Build the graph
        self.memory = MemorySaver()
        self.graph = self._build_graph(self.memory)
        self.config = {"configurable": {"thread_id": "abc123"}}

    def _build_graph(self, memory):
        """Build the chatbot's workflow graph."""

        # Step 1: Generate an AIMessage that may include a tool-call to be sent.
        def query_or_respond(state: MessagesState):
            """Generate tool call for retrieval or respond."""
            llm_with_tools = self.llm.bind_tools([self.retrieve])
            response = llm_with_tools.invoke(state["messages"])
            # MessagesState appends messages to state instead of overwriting
            return {"messages": [response]}

        # Step 2: Execute the retrieval.
        tools = ToolNode([self.retrieve])

        # Step 3: Generate a response using the retrieved content.
        def generate(state: MessagesState):
            """Generate answer."""
            # Get generated ToolMessages
            recent_tool_messages = []
            for message in reversed(state["messages"]):
                if message.type == "tool":
                    recent_tool_messages.append(message)
                else:
                    break
            tool_messages = recent_tool_messages[::-1]

            # Format into prompt
            docs_content = "\n\n".join(doc.content for doc in tool_messages)
            print(docs_content)
            system_message_content = (
                "You are an assistant for question-answering tasks. "
                "Use the following pieces of retrieved context to answer "
                "the question. If the following context don't provide the related answer, "
                "say that you don't know."
                "\n\n"
                f'context: """{docs_content}""" '
            )

            conversation_messages = [
                message
                for message in state["messages"]
                if message.type in ("human", "system")
                or (message.type == "ai" and not message.tool_calls)
            ]
            prompt = [SystemMessage(system_message_content)] + conversation_messages

            # Run
            response = self.llm.invoke(prompt)
            return {"messages": [response]}

        # Initialize graph builder
        graph_builder = StateGraph(MessagesState)

        # Add nodes to the graph
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

        # Compile graph
        return graph_builder.compile(checkpointer=memory)

    def response(self, query: str):
        """Process a user message through the graph."""
        print("query msgs:", query)
        for step in self.graph.stream(
            {"messages": [{"role": "user", "content": query}]},
            stream_mode="values",
            config=self.config,
        ):
            final_message = step["messages"][-1]
        print("query response:", final_message.content)
        print("=" * 30)
        return final_message.content

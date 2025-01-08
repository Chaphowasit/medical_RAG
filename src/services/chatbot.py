from typing import List
from langchain_openai import OpenAI
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from qdrant_client import QdrantClient
from langchain_core.tools import tool
from dotenv import load_dotenv
import os
from adaptors.qdrant_adaptors import Thai2VecEmbedder
import asyncio
import uuid
from langchain_core.documents import Document


class State(MessagesState):
    context: List[Document] = []


class Chatbot:
    def __init__(self, adaptor):
        """Initialize the chatbot with Qdrant adaptor and graph."""
        load_dotenv(override=True)

        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        self.llm = OpenAI(temperature=0.5, api_key=os.getenv("OPENAI_API_KEY"))
        self.thai2vec = Thai2VecEmbedder()

        @tool(response_format="content_and_artifact")
        def retrieve(query: str):
            """Retrieve information related to a query."""
            query_vector = self.thai2vec.get_embedding(query)
            search_results = self.client.query_points(
                collection_name="law",
                query=query_vector,
                limit=10,
            ).points

            retrieved_docs = [
                Document(
                    page_content=point.payload["page_content"],
                    metadata=point.payload["metadata"],
                )
                for point in search_results
            ]

            serialized = "\n\n".join(doc.page_content for doc in retrieved_docs)
            return serialized, retrieved_docs

        set_llm_cache(InMemoryCache())
        self.retrieve = retrieve
        self.llm = ChatOpenAI(model="gpt-4o", max_tokens=8000)
        self.memory = MemorySaver()
        self.graph = self._build_graph(self.memory)
        self.metadata = None

    def _build_graph(self, memory):
        """Build the chatbot's workflow graph."""

        def query_or_respond(state: State):
            """Generate tool call for retrieval or respond."""
            llm_with_tools = self.llm.bind_tools([self.retrieve])
            response = llm_with_tools.invoke(state["messages"])
            return {"messages": [response]}

        tools = ToolNode([self.retrieve])

        def generate(state: State):
            """Generate answer."""
            recent_tool_messages = []
            for message in reversed(state["messages"]):
                if message.type == "tool":
                    recent_tool_messages.append(message)
                else:
                    break
            tool_messages = recent_tool_messages[::-1]

            docs_content = "\n\n".join(doc.content for doc in tool_messages)
            context = {}
            for tool_message in tool_messages:
                list_doc = tool_message.artifact
                for doc in list_doc:
                    source = doc.metadata["source"]
                    page = doc.metadata["page"]
                    if source not in context:
                        context[source] = set()
                    context[source].add(page)

            for key in context:
                context[key] = list(context[key])
            self.metadata = context
            system_message_content = (
                "You are an assistant for question-answering tasks. "
                "Use the provided context to respond clearly, accurately, and do not exceed 80 words in Thai. "
                "If multiple pieces of context have the same content, "
                "use the one with the latest date from their metadata. "
                "If the following context doesn't provide a direct answer, try to infer the answer from the existing information. "
                "If you can't infer a direct answer, say 'ฉันไม่แน่ใจ แต่จากข้อมูลที่มีอยู่ ... '. Then, summarize the existing information to respond as best as you can."
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

            response = self.llm.invoke(prompt, max_tokens=150)

            return {"messages": [response]}

        graph_builder = StateGraph(State)
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

    async def async_wrapper(self, generator):
        """Wrap a generator to allow for async iteration."""
        for item in generator:
            yield item
            await asyncio.sleep(0)

    async def stream_response(self, query: str):
        """Process a user message through the graph."""
        print("query message :", query)
        config = {"thread_id": str(uuid.uuid4())}
        langchain_graph_step = self.async_wrapper(
            self.graph.stream(
                {"messages": [{"role": "user", "content": query}]},
                stream_mode="messages",
                config=config,
            )
        )

        async for message, metadata in langchain_graph_step:
            if metadata["langgraph_node"] == "generate":
                yield message.content, "RAG and " + str(self.metadata), self.metadata
            elif metadata["langgraph_node"] == "query_or_respond":
                yield message.content, "LLM", None

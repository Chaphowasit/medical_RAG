# import os

# from langgraph.graph import MessagesState, StateGraph, END
# from langgraph.prebuilt import ToolNode, tools_condition
# from langchain_core.messages import SystemMessage
# from langchain_openai import ChatOpenAI
# from langgraph.checkpoint.memory import MemorySaver
# from langchain_core.caches import InMemoryCache
# from langchain_core.globals import set_llm_cache

# from qdrant_client import QdrantClient
# from langchain_core.tools import tool
# from dotenv import load_dotenv

# from services.thai_to_vec_embedder import Thai2VecEmbedder
# from services.text_cleaner import TextCleaner


# class Chatbot:
#     def __init__(self, qdrant_client: QdrantClient):
#         """Initialize the chatbot with Qdrant adaptor and graph."""
#         load_dotenv(override=True)
#         self.client = qdrant_client
#         self.thai2vec = Thai2VecEmbedder()
#         self.text_cleaner = TextCleaner()

#         @tool(response_format="content_and_artifact")
#         def retrieve(query: str):
#             """Retrieve information related to a query."""
#             query_vector = self.thai2vec.get_embedding(
#                 self.text_cleaner.preprocess_text(query)
#             )
#             print("query query : ", query)
#             search_results = self.client.query_points(
#                 collection_name="medical",
#                 query=query_vector,
#                 limit=30,
#             )
#             return (
#                 "\n\n".join(
#                     [
#                         f"\nRank: {i+1} from page: {point['payload']['metadata']['page']} \n\n {point['payload']['page_content']}"
#                         for i, point in enumerate(search_results.model_dump()["points"])
#                     ]
#                 ),
#                 search_results,
#             )

#         set_llm_cache(InMemoryCache())

#         self.retrieve = retrieve

#         self.llm = ChatOpenAI(
#             temperature=0.5,
#             api_key=os.getenv("OPENAI_API_KEY"),
#             model="gpt-4o-mini",
#             max_tokens=8000,
#         )

#         self.memory = MemorySaver()
#         self.graph = self._build_graph(self.memory)
#         self.config = {"configurable": {"thread_id": "abc123"}}

#     def _build_graph(self, memory):
#         """Build the chatbot's workflow graph."""

#         def query_or_respond(state: MessagesState):
#             """Generate tool call for retrieval or respond."""
#             llm_with_tools = self.llm.bind_tools([self.retrieve])
#             response = llm_with_tools.invoke(state["messages"])
#             return {"messages": [response]}

#         tools = ToolNode([self.retrieve])

#         def generate(state: MessagesState):
#             """Generate answer."""
#             recent_tool_messages = []
#             for message in reversed(state["messages"]):
#                 if message.type == "tool":
#                     recent_tool_messages.append(message)
#                 else:
#                     break
#             tool_messages = recent_tool_messages[::-1]

#             docs_content = "\n\n".join(doc.content for doc in tool_messages)
#             system_message_content = (
#                 "You are an assistant for question-answering tasks. "
#                 "Use the following pieces of retrieved context to answer "
#                 "the question. If the following context don't provide the related answer, "
#                 "say that you don't know. And don't omit the context."
#                 "\n\n"
#                 f'context: """{docs_content}""" '
#             )
#             print(docs_content)
#             conversation_messages = [
#                 message
#                 for message in state["messages"]
#                 if message.type in ("human", "system")
#                 or (message.type == "ai" and not message.tool_calls)
#             ]
#             prompt = [SystemMessage(system_message_content)] + conversation_messages
#             print("prompt msgs:", prompt)
#             response = self.llm.invoke(prompt)
#             return {"messages": [response], "docs_content": docs_content}

#         graph_builder = StateGraph(MessagesState)

#         graph_builder.add_node(query_or_respond)
#         graph_builder.add_node(tools)
#         graph_builder.add_node(generate)

#         graph_builder.set_entry_point("query_or_respond")
#         graph_builder.add_conditional_edges(
#             "query_or_respond",
#             tools_condition,
#             {END: END, "tools": "tools"},
#         )
#         graph_builder.add_edge("tools", "generate")
#         graph_builder.add_edge("generate", END)

#         return graph_builder.compile(checkpointer=memory)

#     def response(self, query: str):
#         """Process a user message through the graph."""
#         print("query msgs:", query)
#         langchain_graph_step = self.graph.stream(
#             {"messages": [{"role": "user", "content": query}]},
#             stream_mode="values",
#             config=self.config,
#         )
#         last_step = None
#         for step in langchain_graph_step:
#             last_step = step

#         final_message = last_step["messages"][-1]
#         docs_content = last_step["messages"][-2]
#         return final_message.content, docs_content.content

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
                collection_name="medical",
                query=query_vector,
                limit=1,
            )
            return search_results, search_results

        set_llm_cache(InMemoryCache())
        self.retrieve = retrieve
        self.llm = ChatOpenAI(model="gpt-4o", max_tokens=8000)
        self.memory = MemorySaver()
        self.graph = self._build_graph(self.memory)

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
            conversation_messages = [
                message
                for message in state["messages"]
                if message.type in ("human", "system")
                or (message.type == "ai" and not message.tool_calls)
            ]
            prompt = [SystemMessage(system_message_content)] + conversation_messages
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

    async def async_wrapper(self, generator):
        for item in generator:
            yield item
            await asyncio.sleep(0)

    async def stream_response(self, query: str):
        """Process a user message through the graph."""
        print("query msgs:", query)
        config = {"thread_id": str(uuid.uuid4())} 
        langchain_graph_step = self.async_wrapper(
            self.graph.stream(
                {"messages": [{"role": "user", "content": query}]},
                stream_mode="messages",
                config=config,
            )
        )

        async for message, metadata in langchain_graph_step:

            if metadata["langgraph_node"] == "generate" or metadata["langgraph_node"] == "query_or_respond":
                yield message.content

from typing import List
from langchain_openai import OpenAI
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_core.tools import tool
from dotenv import load_dotenv
import os
from adaptors.qdrant_adaptors import Thai2VecEmbedder
import asyncio
import uuid
from langchain_core.documents import Document


class State(MessagesState):
    """
    Represents the state of the chatbot, holding context as a list of documents.

    Attributes:
        context (List[Document]): A list of documents representing the context of the chatbot's current state.
    """
    context: List[Document] = []


class Chatbot:
    """
    A class that implements a chatbot powered by LLMs (Large Language Models) to interact with a user and provide legal information.

    The chatbot retrieves legal information from a database using Qdrant and interacts with users using a defined workflow graph.

    Args:
        client: The Qdrant client instance used to query the Qdrant database.
        collection_name: The name of the collection in Qdrant from which legal information will be retrieved.
    """
    def __init__(self, client, collection_name):
        """
        Initializes the chatbot with the required Qdrant client, LLM, embedding model, and workflow graph.

        Args:
            client: The Qdrant client instance used to query the Qdrant database.
            collection_name: The name of the collection in Qdrant to retrieve legal information from.
        """
        load_dotenv(override=True)

        self.client = client
        self.llm = OpenAI(temperature=0.5, api_key=os.getenv("OPENAI_API_KEY"))
        self.thai2vec = Thai2VecEmbedder()
        self.collection_name = collection_name

        @tool(response_format="content_and_artifact")
        def retrieve(query: str):
            """
            Retrieve information relevant to the specified query within the law domain.

            Args:
                query (str): The query provided by the user to retrieve information.

            Returns:
                tuple: A tuple containing the serialized documents and the list of retrieved documents.
            """
            query_vector = self.thai2vec.get_embedding(query)
            search_results = self.client.query_points(
                collection_name=self.collection_name,
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

            serialized = "\n\n".join(
                f"--- Document Start ---\n"
                f"Page Content:\n{doc.page_content}\n\n"
                f"Metadata:\n{doc.metadata}\n"
                f"--- Document End ---"
                for doc in retrieved_docs
            )
            return serialized, retrieved_docs

        set_llm_cache(InMemoryCache())
        self.retrieve = retrieve
        self.llm = ChatOpenAI(model="gpt-4o", max_tokens=8000)
        self.memory = MemorySaver()
        self.config = {"configurable":{"thread_id": str(uuid.uuid4())}}
        self.graph = self._build_graph(self.memory)
        self.metadata = None

    def _build_graph(self, memory):
        """
        Build the chatbot's workflow graph which manages how messages are processed.

        This function defines the different nodes and how they interact to generate the chatbot's response.

        Args:
            memory (MemorySaver): The memory manager to save and restore state across graph executions.

        Returns:
            StateGraph: The compiled workflow graph that controls the chatbot's behavior.
        """
        def query_or_respond(state: State):
            """
            Generate tool call for retrieval or respond with a Thai-only response.

            Args:
                state (State): The current state containing "messages" to be processed.

            Returns:
                dict: A dictionary containing the "messages" with a Thai-only response.
            """
            thai_prompt = (
                "Respond only in Thai, regardless of the language of the received message, and use male pronouns and speech style."
            )
            state["messages"].insert(0, {"role": "system", "content": thai_prompt})
            llm_with_tools = self.llm.bind_tools([self.retrieve])
            response = llm_with_tools.invoke(state["messages"])
            return {"messages": [response]}

        tools = ToolNode([self.retrieve])

        def generate(state: State):
            """
            Generate an answer based on the context and the query.

            Args:
                state (State): The current state containing "messages" to be processed.

            Returns:
                dict: A dictionary containing the "messages" with a generated response.
            """
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
                context[key] = sorted([element + 1 for element in context[key]])
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
        """
        Wrap a generator to allow for async iteration.

        Args:
            generator: The generator to be wrapped for async iteration.

        Yields:
            item: Each item yielded by the generator, asynchronously.
        """
        for item in generator:
            yield item
            await asyncio.sleep(0)

    async def stream_response(self, query: str):
        """
        Process a user message through the graph and yield results in real-time.

        Args:
            query (str): The user input message for the chatbot to process.

        Yields:
            tuple: A tuple containing the response content, source (either "RAG" or "LLM"), and metadata.
        """
        print("query message :", query)

        langchain_graph_step = self.async_wrapper(
            self.graph.stream(
                {"messages": [{"role": "user", "content": query}]},
                stream_mode="messages",
                config=self.config,
            )
        )

        async for message, metadata in langchain_graph_step:
            if metadata["langgraph_node"] == "generate":
                yield message.content, "RAG", str(self.metadata)
            elif metadata["langgraph_node"] == "query_or_respond":
                yield message.content, "LLM", None

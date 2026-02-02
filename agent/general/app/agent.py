"""LangChain ReAct agent setup."""

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI

from .config import Config, get_config
from .tools import web_search_tool, web_fetch_tool, exec_tool, browser_tool, cron_tool


REACT_PROMPT = PromptTemplate.from_template("""You are a helpful AI assistant with access to various tools. Use these tools to help answer the user's questions and complete tasks.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}""")


def create_llm(config: Config):
    """Create the LLM based on configuration."""
    if config.openai_api_key:
        return ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=0,
        )
    else:
        return Ollama(
            base_url=config.ollama_host,
            model=config.ollama_model,
        )


def create_agent_executor(config: Config | None = None) -> AgentExecutor:
    """Create the agent executor with tools."""
    if config is None:
        config = get_config()

    llm = create_llm(config)

    tools = [
        web_search_tool,
        web_fetch_tool,
        exec_tool,
        browser_tool,
        cron_tool,
    ]

    agent = create_react_agent(llm, tools, REACT_PROMPT)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
    )

    return executor


async def run_agent(message: str, config: Config | None = None) -> str:
    """Run the agent with a message and return the response."""
    executor = create_agent_executor(config)
    result = await executor.ainvoke({"input": message})
    return result.get("output", str(result))


def run_agent_sync(message: str, config: Config | None = None) -> str:
    """Run the agent synchronously with a message and return the response."""
    executor = create_agent_executor(config)
    result = executor.invoke({"input": message})
    return result.get("output", str(result))

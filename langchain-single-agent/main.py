import os
from typing import cast

import requests
from dotenv import load_dotenv
from langchain import hub
from langchain.agents import AgentExecutor, BaseSingleActionAgent, create_react_agent
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.pydantic_v1 import SecretStr
from langchain_openai import ChatOpenAI

load_dotenv(encoding="utf-8")

TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
WEATHERSTACK_API_KEY = os.getenv('WEATHERSTACK_API_KEY')

if not DEEPSEEK_API_KEY:
    raise RuntimeError("环境变量 DEEPSEEK_API_KEY 未设置，请检查 .env 文件")

if not TAVILY_API_KEY:
    raise RuntimeError("环境变量 TAVILY_API_KEY 未设置，请检查 .env 文件")

if not WEATHERSTACK_API_KEY:
    raise RuntimeError("环境变量 WEATHERSTACK_API_KEY 未设置，请检查 .env 文件")

search_tool = TavilySearchResults(max_results=2)

@tool
def get_weather_data(city: str) -> str:
    """
    Fetch current weather information for a city.
    """

    url = (
        f"https://api.weatherstack.com/current?"
        f"access_key={WEATHERSTACK_API_KEY}&query={city}"
    )

    response = requests.get(url)

    data = response.json()

    if "current" not in data:
        return f"Could not fetch weather data for {city}"

    return (
        f"City: {city}\n"
        f"Temperature: {data['current']['temperature']}°C\n"
        f"Weather: {data['current']['weather_descriptions'][0]}\n"
        f"Humidity: {data['current']['humidity']}%"
    )

llm = ChatOpenAI(
    base_url="https://api.deepseek.com",
    model="deepseek-flash",
    api_key=SecretStr(DEEPSEEK_API_KEY),
)

prompt = hub.pull("hwchase17/react")

tools = [search_tool, get_weather_data]

agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=cast(BaseSingleActionAgent, agent),
    tools=tools,
    verbose=True,
)

if __name__ == "__main__":
    response = agent_executor.invoke({
        "input": (
            "Find the capital of Germany"
            "and then find its current weather."
        )
    })
    
    print(response["output"])
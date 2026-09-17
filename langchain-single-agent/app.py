import streamlit as st

from main import agent_executor

st.set_page_config(
    page_title="Agentic AI Assistant",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Agentic AI Assistant")
st.markdown("Search + Weather AI Agent using LangChain")

user_query = st.text_input(
    "Enter your query",
    placeholder="Example: Find the capital of Germany and current weather"
)

if st.button("Run Agent"):
    if user_query:
        with st.spinner("Agent is thinking..."):
            try:
                response = agent_executor.invoke({
                    "input": user_query
                })

                st.success("Response Generated")

                st.markdown("## Final Response")
                st.write(response["output"])

            except Exception as e:
                st.error(f"Error: {e!s}")
    else:
        st.warning("Please enter a query")
# Multi-Agent AWS Architecture and Cost Analysis System
# Uses Agents as Tools pattern with MCP (Model Context Protocol) servers

from datetime import datetime

from mcp import StdioServerParameters, stdio_client
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from io import StringIO
from bedrock_agentcore import BedrockAgentCoreApp

# Initialize AgentCore application for deployment
app = BedrockAgentCoreApp()
agent = Agent()


# MCP Client for AWS Documentation - provides access to AWS service documentation
aws_docs_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx", args=["awslabs.aws-documentation-mcp-server@latest"]
        )
    )
)

# MCP Client for AWS Pricing - provides cost analysis and pricing data
cost_analysis_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx", args=["awslabs.aws-pricing-mcp-server@latest"]
        )
    )
)

# Configure the LLM model for all agents
bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0", 
    temperature=0.7, 
)

COST_ANALYSIS_AGENT_PROMPT = """
You are a cost analysis specialist with expertise in:
- Analyzing AWS cost structures and pricing models
- Creating cost comparison scenarios
- Identifying cost-saving opportunities across AWS services
- Analyzing Reserved Instance and Savings Plan opportunities
- Providing detailed cost breakdowns by service, region, and usage patterns
Use the cost analysis tools to provide accurate financial projections, cost estimation and optimization strategies.
"""

SA_AGENT_PROMPT = """
You are an AWS Certified Solutions Architect with expertise in:
- Provide recommendation of best usage of AWS services based on customers use cases and aligned to the Well Architected Framework
- Performing comprehensive cost analysis and optimization
"""

@tool
def cost_analysis_specialist(query: str) -> str:
    """
    Specialized agent for AWS cost analysis and optimization strategies.
    Combines AWS documentation and pricing tools for comprehensive cost analysis.
    """
    # Initialize MCP clients and combine their tools
    with aws_docs_client, cost_analysis_client:
        all_tools = (
            aws_docs_client.list_tools_sync() + cost_analysis_client.list_tools_sync()
        )
        # Create specialized cost analysis agent with combined toolset
        cost_agent = Agent(
            system_prompt=COST_ANALYSIS_AGENT_PROMPT,
            tools=all_tools,
            model=bedrock_model,
        )
        return str(cost_agent(query))

@tool
def architecture_analyst(query: str) -> str:
    """
    Specialized agent for AWS architecture design and Well-Architected Framework guidance.
    Uses AWS documentation tools to provide architectural recommendations.
    """
    # Initialize AWS documentation client for architecture guidance
    with aws_docs_client:
        all_tools = (
            aws_docs_client.list_tools_sync()
        )
        # Create specialized solutions architect agent
        sa_agent = Agent(
            system_prompt=SA_AGENT_PROMPT, 
            tools=all_tools, 
            model=bedrock_model
        )
        return str(sa_agent(query))

def create_cost_and_architecture_orchestrator():
    """
    Creates the main orchestrator agent implementing the "Agents as Tools" pattern.
    Coordinates specialized agents to provide comprehensive AWS architecture and cost analysis.
    """

    COST_AND_ARCHITECTURE_ORCHESTRATOR_PROMPT = """
    You are a Cloud Pricing and Cost analyst.
    
    Your role is to:
    1. Understand customer technical requirement
    2. Delegate specific tasks to specialized agents
    
    Available tool agents:
    - architecture_analyst: For services and architectural best practices
    - cost_analysis_specialist: For cost analysis and financial projections
    
    Provide a very high level recomendation of services configuration and an estimated cost of usage of AWS services
    """

    # Create orchestrator with specialized agents as tools
    orchestrator = Agent(
        system_prompt=COST_AND_ARCHITECTURE_ORCHESTRATOR_PROMPT,
        tools=[
            architecture_analyst,
            cost_analysis_specialist,
        ],
        model=bedrock_model,
    )

    return orchestrator



@app.entrypoint
async def invoke(payload):
    """Main entrypoint for the Cloud Architect Analyst Agent"""
    # Extract user message from payload (supports both "prompt" key and direct payload)
    user_message = payload.get("prompt", payload)
    
    # Create the orchestrator agent that coordinates specialist agents
    orchestrator = create_cost_and_architecture_orchestrator()
    agent = orchestrator

    # Stream responses in real-time for better user experience
    stream = agent.stream_async(user_message)
    async for event in stream:
        if "data" in event:
            yield event["data"]          # Stream individual data chunks
        elif "message" in event:
            yield event["message"]       # Stream complete message parts

# Run the agent locally for testing or deploy to AgentCore runtime
if __name__ == "__main__":
    app.run()  # Starts local server on port 8080

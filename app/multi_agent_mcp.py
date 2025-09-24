from datetime import datetime

from mcp import StdioServerParameters, stdio_client
from strands import Agent, tool
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from io import StringIO
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()
agent = Agent()


aws_docs_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx", args=["awslabs.aws-documentation-mcp-server@latest"]
        )
    )
)

# Cost Analysis MCP Client
cost_analysis_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx", args=["awslabs.aws-pricing-mcp-server@latest"]
        )
    )
)

bedrock_model = BedrockModel(
    model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    # model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
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
    This tool agent specializes in AWS cost analysis and optimization strategies.
    """
    with aws_docs_client, cost_analysis_client:
        all_tools = (
            aws_docs_client.list_tools_sync() + cost_analysis_client.list_tools_sync()
        )
        cost_agent = Agent(
            system_prompt=COST_ANALYSIS_AGENT_PROMPT,
            tools=all_tools,
            model=bedrock_model,
        )
        return str(cost_agent(query))

@tool
def architecture_analyst(query: str) -> str:
    """
    This tool agent specializes in AWS architecture design and cost optimization.
    """
    with aws_docs_client:
        all_tools = (
            aws_docs_client.list_tools_sync()
        )
        sa_agent = Agent(
            system_prompt=SA_AGENT_PROMPT, 
            tools=all_tools, 
            model=bedrock_model
        )
        return str(sa_agent(query))
        # Extract diagram path if created
#        if "diagram" in str(response).lower():
#            return f"{response}\n\nNote: Check the output for the diagram file path."
#        return str(response)


def create_cost_and_architecture_orchestrator():
    """
    Create the main orchestrator agent for prividing architecture and AWS services design best practices.
    This orchestrator coordinates all specialized tool agents to deliver
    a comprehensive analysis.
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

    orchestrator = Agent(
        system_prompt=COST_AND_ARCHITECTURE_ORCHESTRATOR_PROMPT,
        tools=[
            architecture_analyst,
            cost_analysis_specialist,
#            presentation_creator,
        ],
        model=bedrock_model,
    )

    return orchestrator



@app.entrypoint
async def invoke(payload):
    """Cloud Architect Analyst Agent"""
    user_message = payload.get("prompt", payload)
    orchestrator = create_cost_and_architecture_orchestrator()
    agent = orchestrator

    # Stream responses as they're generated
    stream = agent.stream_async(user_message)
    async for event in stream:
        if "data" in event:
            yield event["data"]          # Stream data chunks
        elif "message" in event:
            yield event["message"]       # Stream message parts

if __name__ == "__main__":
    app.run()

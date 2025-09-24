import boto3
import json
import sys
import re
  
# Initialize the Bedrock AgentCore client
client = boto3.client('bedrock-agentcore')


input_text = "Design an arquitecture for an e-commerce platform with 1M daily users"

payload = json.dumps({"prompt": input_text}).encode()

response = client.invoke_agent_runtime(
    agentRuntimeArn="<UPDATE_WITH_AGENT_ARN>",
    qualifier="DEFAULT",
    payload=payload
)

# Process and print the response
if "text/event-stream" in response.get("contentType", ""):
    # Handle streaming response
    content = []
    full_text = ""
    
    for line in response["response"].iter_lines(chunk_size=10):
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                line = line[6:]
                
                # Skip any JSON chunks containing role information or content structures
                if (re.match(r'^"?{.*"role":', line) or 
                    re.match(r'^"?{.*"content":', line) or
                    line.strip() == '"' or  # Empty quote chunks
                    line.strip() == '}'     # Closing brace chunks
                   ):
                    continue
                    
                # Remove quotes from the beginning and end if present
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                
                # Handle escaped newlines properly
                line = line.replace("\\n", "\n")
                
                # Print the chunk without newline at the end
                sys.stdout.write(line)
                sys.stdout.flush()
                
                # Add to full content (but we won't print it at the end)
                content.append(line)
                full_text += line
    
    # Just print a newline at the end for a cleaner finish
    # but NO summary/duplication
    print()

elif response.get("contentType") == "application/json":
    # Handle standard JSON response
    content = []
    for chunk in response.get("response", []):
        content.append(chunk.decode('utf-8'))
    print(json.loads(''.join(content)))
  
else:
    # Print raw response for other content types
    formatted_content = response['result']
    print(formatted_content)
import asyncio
import sys
import os
import json
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
from mcp.types import CallToolRequest, ClientCapabilities

async def test_mcp_client():
    # Set environment variables if needed
    env = os.environ.copy()
    
    # Path to the server script
    server_script = os.path.join(os.getcwd(), "main_news_mcp.py")
    
    print(f"Starting MCP server from: {server_script}")
    
    # Server parameters
    from mcp.client.stdio import StdioServerParameters
    server_params = StdioServerParameters(
        command=sys.executable, 
        args=[server_script], 
        env=env
    )
    
    server_process = stdio_client(server_params)

    async with server_process as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # List tools
            print("\n--- Listing Tools ---")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")
            
            # Call start_news_collection
            print("\n--- Calling start_news_collection ---")
            try:
                result = await session.call_tool("start_news_collection", arguments={"force": True})
                print("Result:")
                for content in result.content:
                    if content.type == "text":
                        print(content.text)
            except Exception as e:
                print(f"Error calling tool: {e}")
                
            # Wait a bit to let background tasks run (though we can't see their output easily in stdio mode)
            print("\nWaiting for 5 seconds...")
            await asyncio.sleep(5)
            
            print("\nTest completed.")

if __name__ == "__main__":
    asyncio.run(test_mcp_client())

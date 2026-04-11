import sys
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from tools import register_tools
from transport import create_mcp_app

mcp = FastMCP("HelloVault-May")

@mcp.tool()
async def ping() -> str:
    """#S_EN: [TOOL] Standard health check"""
    return "⟦✓⟧ PONG from HelloVault-May!"
# Подключаем инструменты
register_tools(mcp)

# Промпты (оставляем здесь для наглядности)
@mcp.prompt("strategic-decision")
def strategic_decision(topic: str) -> str:
    return f"Вызови 'get_verified_brief' для '{topic}' и прими решение."

if __name__ == "__main__":
    if "stdio" in sys.argv:
        mcp.run()
    else:
        sse = SseServerTransport("messages")
        app = create_mcp_app(mcp, sse)
        print("🌀 MCP-May Server LIVE: http://localhost:8001/mcp")
        uvicorn.run(app, host="0.0.0.0", port=8001)

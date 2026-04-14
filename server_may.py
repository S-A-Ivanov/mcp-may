import sys
import logging
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from tools import register_tools
from transport import create_mcp_app

# Настройка логирования для сервера
logger = logging.getLogger(__name__)

mcp = FastMCP("HelloVault-May")


@mcp.tool()
async def ping() -> str:
    """#S_EN: [TOOL] Standard health check.
    
    Returns:
        Строка подтверждения работоспособности сервера.
    """
    return "⟦✓⟧ PONG from HelloVault-May!"


# Подключаем инструменты
register_tools(mcp)


# Промпты (оставляем здесь для наглядности)
@mcp.prompt("strategic-decision")
def strategic_decision(topic: str) -> str:
    """Генерация промпта для стратегического решения.
    
    Args:
        topic: Тема для принятия решения.
        
    Returns:
        Строка-инструкция для выполнения.
    """
    return f"Вызови 'get_verified_brief' для '{topic}' и прими решение."


if __name__ == "__main__":
    if "stdio" in sys.argv:
        mcp.run()
    else:
        sse = SseServerTransport("messages")
        app = create_mcp_app(mcp, sse)
        logger.info("🌀 MCP-May Server LIVE: http://localhost:8001/mcp")
        print("🌀 MCP-May Server LIVE: http://localhost:8001/mcp")
        uvicorn.run(app, host="0.0.0.0", port=8001)

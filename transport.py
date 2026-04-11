from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse

def create_mcp_app(mcp, sse_transport):
    """Создает Starlette приложение с настроенным MCP хендлером"""
    
    async def mcp_handler(scope, receive, send):
        if scope["type"] == "http":
            if scope["method"] == "GET":
                async with sse_transport.connect_sse(scope, receive, send) as (read, write):
                    # Безопасный доступ к ядру сервера
                    server_obj = getattr(mcp, "_mcp_server", getattr(mcp, "server", None))
                    await server_obj.run(read, write, server_obj.create_initialization_options())
            elif scope["method"] == "POST":
                await sse_transport.handle_post_message(scope, receive, send)

    return Starlette(routes=[
        Mount("/mcp", app=mcp_handler),
        Route("/health", endpoint=lambda r: JSONResponse({"status": "ok"}))
    ])

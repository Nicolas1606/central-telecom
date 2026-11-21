"""Cliente local opcional para usar o mesmo índice via protocolo MCP."""
import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .knowledge import ROOT
from .provider import Unavailable

async def _search(query,domain,mode):
    params=StdioServerParameters(command=sys.executable,args=["-m","central.mcp_server"],cwd=str(ROOT))
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result=await session.call_tool("buscar_politica",{"pergunta":query,"dominio":domain,"metodo":mode})
            if result.isError:
                raise ValueError("Falha na ferramenta de busca")
            return result.structuredContent["result"]

def retrieve(query,domain,mode):
    try:
        return asyncio.run(asyncio.wait_for(_search(query,domain,mode),timeout=20))
    except Exception as exc:
        raise Unavailable("Busca MCP indisponível") from exc

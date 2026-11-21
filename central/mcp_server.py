"""Servidor MCP stdio para explorar a base pública de políticas. Sem acesso ao CRM."""
from typing import Literal
from mcp.server.fastmcp import FastMCP
from .knowledge import Index

server = FastMCP("Politicas Telecom")
index = Index()

@server.tool()
def buscar_politica(pergunta: str, dominio: Literal["cobranca","suporte","cancelamento"] | None = None,
                   metodo: Literal["lexical","semantic","hybrid"] = "hybrid") -> list[dict]:
    """Retorna até três passagens relevantes da operadora fictícia e seus IDs."""
    return index.search(pergunta[:1200],dominio,metodo)

if __name__=="__main__":
    server.run(transport="stdio")

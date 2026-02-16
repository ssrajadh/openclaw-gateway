"""Direct Tavily API client."""

import httpx
from app.config import get_settings


class TavilySearchError(Exception):
    """Raised when Tavily search fails."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


async def tavily_search(query: str, max_results: int = 5) -> dict:
    """
    Call Tavily API directly for web search.
    Returns search results.
    """
    settings = get_settings()
    
    # Check if we have a Tavily API key in the .env
    tavily_key = getattr(settings, "tavily_api_key", "")
    if not tavily_key:
        raise TavilySearchError("TAVILY_API_KEY not configured in gateway .env")
    
    url = "https://api.tavily.com/search"
    headers = {
        "Content-Type": "application/json",
    }
    
    body = {
        "api_key": tavily_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
        "include_raw_content": False,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=body, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "ok": True,
                "result": {
                    "answer": data.get("answer", ""),
                    "results": data.get("results", []),
                    "query": query,
                }
            }
        else:
            error_text = resp.text
            raise TavilySearchError(f"Tavily API error ({resp.status_code}): {error_text}")
            
    except httpx.RequestError as e:
        raise TavilySearchError(f"Network error calling Tavily: {str(e)}")
    except Exception as e:
        raise TavilySearchError(f"Tavily search failed: {str(e)}")

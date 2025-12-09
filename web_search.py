import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# Keywords to enhance security-related searches
SECURITY_KEYWORDS = [
    'exploit', 'vulnerability', 'CVE', 'hack', 'pentest', 'security',
    'kali', 'nmap', 'metasploit', 'burp', 'sqlmap', 'payload', 'shell',
    'bypass', 'injection', 'XSS', 'CSRF', 'reverse', 'backdoor'
]

def search_web(query: str, max_results: int = 5) -> str:
    """
    Realiza una búsqueda avanzada usando DuckDuckGo.
    Optimizado para resultados técnicos de ciberseguridad.
    
    Args:
        query: La consulta de búsqueda
        max_results: Número máximo de resultados (default: 5)
    
    Returns:
        String formateado con los resultados o mensaje de error
    """
    try:
        logger.info(f"🔍 Web search: {query}")
        
        # Enhance query if it's security-related
        enhanced_query = query
        query_lower = query.lower()
        
        # Add context for security searches
        if any(kw in query_lower for kw in ['como', 'how', 'qué es', 'what is']):
            if any(kw in query_lower for kw in SECURITY_KEYWORDS):
                enhanced_query = f"{query} tutorial guide 2024"
        
        results = []
        with DDGS() as ddgs:
            ddg_gen = ddgs.text(
                enhanced_query, 
                region='wt-wt',      # Worldwide (no location bias)
                safesearch='off',    # No censorship
                timelimit='y',       # Last year (fresh info)
                max_results=max_results
            )
            
            for i, r in enumerate(ddg_gen, 1):
                title = r.get('title', 'No Title')
                link = r.get('href', '#')
                body = r.get('body', '')
                
                # Clean and format
                body = body.replace('\n', ' ').strip()
                if len(body) > 200:
                    body = body[:200] + '...'
                
                results.append(
                    f"[{i}] {title}\n"
                    f"    🔗 {link}\n"
                    f"    📝 {body}\n"
                )
        
        if not results:
            return "⚠️ No se encontraron resultados relevantes."
        
        formatted = "\n".join(results)
        logger.info(f"Found {len(results)} web results")
        
        return formatted

    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"⚠️ Error en búsqueda web: {str(e)}"


if __name__ == "__main__":
    # Test
    print(search_web("nmap scan techniques 2024"))


import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def search_web(query, max_results=2):
    """
    Realiza una búsqueda avanzada usando la librería oficial de DuckDuckGo.
    Optimizado para obtener resultados técnicos y sin filtros de burbuja.
    """
    try:
        logger.info(f"Searching web (DDGS) for: {query}")
        
        results = []
        with DDGS() as ddgs:
            # Usamos 'text' para búsqueda general. 
            # backend="api" suele ser más permisivo.
            ddg_gen = ddgs.text(
                query, 
                region='wt-wt', # Región mundial (sin filtro local)
                safesearch='off', # SafeSearch APAGADO (Sin censura)
                timelimit='y', # Último año (información fresca)
                max_results=max_results
            )
            
            for r in ddg_gen:
                title = r.get('title', 'No Title')
                link = r.get('href', '#')
                body = r.get('body', '')
                
                results.append(f"Title: {title}\nLink: {link}\nSummary: {body}\n")
        
        if not results:
            return "No se encontraron resultados relevantes en la web."
            
        return "\n---\n".join(results)

    except Exception as e:
        logger.error(f"Error searching web with DDGS: {e}")
        # Fallback a mensaje de error simple
        return f"Error de búsqueda: {str(e)}"

if __name__ == "__main__":
    # Test
    print(search_web("kali linux exploit database 2024"))

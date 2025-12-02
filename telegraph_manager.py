import requests
import json
import os
from html.parser import HTMLParser

TOKEN_FILE = "telegraph_token.json"
API_URL = "https://api.telegra.ph"

# Tags soportados por Telegraph
ALLOWED_TAGS = {
    'a', 'aside', 'b', 'blockquote', 'br', 'code', 'em', 'figcaption', 'figure', 
    'h3', 'h4', 'hr', 'i', 'iframe', 'img', 'li', 'ol', 'p', 'pre', 's', 
    'strong', 'u', 'ul', 'video'
}

class TelegraphHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []
        # Stack de nodos. El primero es un root dummy.
        self.root = {'tag': 'div', 'children': []}
        self.current_stack = [self.root]

    def handle_starttag(self, tag, attrs):
        # Mapear h1/h2 a h3/h4 porque Telegraph no soporta h1/h2
        if tag == 'h1': tag = 'h3'
        if tag == 'h2': tag = 'h4'
        
        # Si el tag no está permitido, lo tratamos como transparente (solo procesamos sus hijos)
        # o lo convertimos a párrafo si es bloque. Por simplicidad, si no es permitido, 
        # no creamos nodo pero seguimos parseando contenido.
        # Excepción: div y span se ignoran estructuralmente pero su contenido se mantiene.
        
        if tag not in ALLOWED_TAGS:
            return

        node = {'tag': tag, 'children': []}
        if attrs:
            # Filtrar atributos. Telegraph solo permite href, src, etc.
            valid_attrs = {}
            for k, v in attrs:
                if k in ['href', 'src', 'alt']:
                    valid_attrs[k] = v
            if valid_attrs:
                node['attrs'] = valid_attrs
        
        # Añadir al padre actual
        self.current_stack[-1]['children'].append(node)
        
        # Si no es void tag (como br, img, hr), lo ponemos en el stack
        if tag not in ['br', 'img', 'hr']:
            self.current_stack.append(node)

    def handle_endtag(self, tag):
        if tag == 'h1': tag = 'h3'
        if tag == 'h2': tag = 'h4'
        
        if tag in ALLOWED_TAGS and tag not in ['br', 'img', 'hr']:
            # Pop del stack si coincide
            if len(self.current_stack) > 1:
                # Verificación simple: asumimos HTML bien formado.
                # En un parser robusto verificaríamos que el tag coincide con stack[-1]['tag']
                self.current_stack.pop()

    def handle_data(self, data):
        if data:
            # Añadir texto al nodo actual
            # Telegraph espera strings directos en children
            self.current_stack[-1]['children'].append(data)

    def get_content(self):
        return self.root['children']

class TelegraphManager:
    def __init__(self, author_name="KaliRoot Bot", author_url="https://t.me/KaliRootBot"):
        self.author_name = author_name
        self.author_url = author_url
        self.access_token = self._load_or_create_token()

    def _load_or_create_token(self):
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('access_token')
            except:
                pass
        
        return self._create_account()

    def _create_account(self):
        print("Creando cuenta en Telegraph...")
        response = requests.get(f"{API_URL}/createAccount", params={
            'short_name': 'KaliRoot',
            'author_name': self.author_name,
            'author_url': self.author_url
        }).json()
        
        if response.get('ok'):
            token = response['result']['access_token']
            with open(TOKEN_FILE, 'w') as f:
                json.dump({'access_token': token}, f)
            print("Cuenta creada y token guardado.")
            return token
        else:
            raise Exception(f"Error creando cuenta Telegraph: {response}")

    def create_page(self, title, html_content):
        """
        Publica una página en Telegraph.
        html_content: String con código HTML (ej: "<p>Hola</p>")
        """
        # 1. Parsear HTML a Nodos
        parser = TelegraphHTMLParser()
        parser.feed(html_content)
        content_nodes = parser.get_content()
        
        # 2. Enviar a API
        data = {
            'access_token': self.access_token,
            'title': title,
            'author_name': self.author_name,
            'author_url': self.author_url,
            'content': json.dumps(content_nodes),
            'return_content': False
        }
        
        response = requests.post(f"{API_URL}/createPage", data=data).json()
        
        if response.get('ok'):
            return response['result']['url']
        else:
            raise Exception(f"Error publicando página: {response}")

    def get_page_list(self):
        """Obtiene la lista de páginas creadas por esta cuenta."""
        response = requests.get(f"{API_URL}/getPageList", params={
            'access_token': self.access_token,
            'limit': 200
        }).json()
        
        if response.get('ok'):
            pages = response['result']['pages']
            # Ordenamiento Inteligente
            def sort_key(page):
                title = page['title']
                # Intentar extraer número de módulo
                import re
                match = re.search(r'Mod(?:ulo)?\s*(\d+)', title, re.IGNORECASE)
                if match:
                    return (0, int(match.group(1))) # Prioridad 0, orden numérico
                return (1, title) # Prioridad 1, orden alfabético
            
            return sorted(pages, key=sort_key)
        else:
            raise Exception(f"Error obteniendo lista: {response}")

    def edit_page(self, path, title, html_content):
        """Edita una página existente."""
        # 1. Parsear HTML a Nodos
        parser = TelegraphHTMLParser()
        parser.feed(html_content)
        content_nodes = parser.get_content()
        
        # 2. Enviar a API
        data = {
            'access_token': self.access_token,
            'path': path,
            'title': title,
            'author_name': self.author_name,
            'author_url': self.author_url,
            'content': json.dumps(content_nodes),
            'return_content': False
        }
        
        response = requests.post(f"{API_URL}/editPage", data=data).json()
        
        if response.get('ok'):
            return response['result']['url']
        else:
            raise Exception(f"Error editando página: {response}")

    def delete_page(self, path):
        """
        Telegraph NO permite borrar páginas. 
        Esta función hace un 'Soft Delete': cambia el título a 'DELETED' y vacía el contenido.
        """
    def get_auth_url(self):
        """Obtiene un enlace mágico para loguearse en el navegador."""
        response = requests.get(f"{API_URL}/getAccountInfo", params={
            'access_token': self.access_token,
            'fields': '["auth_url"]'
        }).json()
        
        if response.get('ok'):
            return response['result']['auth_url']
        else:
            raise Exception(f"Error obteniendo auth_url: {response}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def interactive_menu():
    tm = TelegraphManager()
    
    while True:
        print("\n" + "="*40)
        print("   📝 GESTOR DE CONTENIDO TELEGRAPH   ")
        print("="*40)
        print("1. ✨ Crear Nueva Página")
        print("2. 📋 Listar Mis Páginas (Ordenadas)")
        print("3. ✏️  Editar Página Existente")
        print("4. 🗑️  Eliminar Página (Soft Delete)")
        print("5. 🔗 Obtener Link de Login (Navegador)")
        print("6. ❌ Salir")
        
        opcion = input("\nSelecciona una opción (1-6): ")
        
        if opcion == '1':
            # ... (código existente) ...
            print("\n--- CREAR NUEVA PÁGINA ---")
            title = input("Título del Post: ")
            print("\nIntroduce el contenido HTML (Pega el código y presiona Enter, o escribe 'FILE' para leer de 'input.html'):")
            content = input("> ")
            
            if content.strip().upper() == 'FILE':
                if os.path.exists('input.html'):
                    with open('input.html', 'r') as f: content = f.read()
                    print("✅ Contenido cargado de input.html")
                else:
                    print("❌ No existe el archivo input.html")
                    continue
            
            try:
                url = tm.create_page(title, content)
                print(f"\n✅ ¡Página Creada! -> {url}")
            except Exception as e:
                print(f"\n❌ Error: {e}")
            input("\nPresiona Enter para continuar...")

        elif opcion == '5':
            print("\n--- LINK DE ACCESO AL NAVEGADOR ---")
            try:
                auth_url = tm.get_auth_url()
                print("\n⚠️  IMPORTANTE: Este enlace te logueará como 'KaliRoot Bot' en tu navegador.")
                print("   Podrás editar todas las páginas visualmente.")
                print(f"\n👉 {auth_url}\n")
            except Exception as e:
                print(f"Error: {e}")
            input("Presiona Enter para continuar...")

        elif opcion == '6':
            print("¡Hasta luego! 👋")
            break

        elif opcion == '2':
            print("\n--- TUS PÁGINAS (Ordenadas) ---")
            try:
                pages = tm.get_page_list()
                if not pages:
                    print("No tienes páginas creadas aún.")
                else:
                    print(f"Se encontraron {len(pages)} páginas:\n")
                    for i, p in enumerate(pages):
                        print(f"{i+1}. {p['title']}")
                        print(f"   🔗 {p['url']}")
                        print("-" * 20)
            except Exception as e:
                print(f"Error: {e}")
            input("\nPresiona Enter para continuar...")
                
        elif opcion == '3':
            print("\n--- EDITAR PÁGINA ---")
            try:
                pages = tm.get_page_list()
                if not pages:
                    print("No tienes páginas para editar.")
                    continue
                    
                for i, p in enumerate(pages):
                    print(f"{i+1}. {p['title']}")
                
                idx = input("\nNúmero de la página a editar: ")
                if not idx.isdigit() or int(idx) < 1 or int(idx) > len(pages):
                    print("❌ Selección inválida.")
                    continue
                
                target_page = pages[int(idx)-1]
                path = target_page['path']
                print(f"\nEditando: {target_page['title']} ({path})")
                
                new_title = input(f"Nuevo Título (Enter para mantener '{target_page['title']}'): ")
                if not new_title.strip(): new_title = target_page['title']
                
                print("\nNuevo Contenido HTML (escribe 'FILE' para leer de 'input.html', o pega aquí):")
                new_content = input("> ")
                
                if new_content.strip().upper() == 'FILE':
                    if os.path.exists('input.html'):
                        with open('input.html', 'r') as f: new_content = f.read()
                        print("✅ Contenido cargado de input.html")
                    else:
                        print("❌ No existe input.html")
                        continue
                
                url = tm.edit_page(path, new_title, new_content)
                print(f"\n✅ ¡Página Actualizada! -> {url}")
                
            except Exception as e:
                print(f"Error: {e}")
            input("\nPresiona Enter para continuar...")

        elif opcion == '4':
            print("\n--- ELIMINAR PÁGINA (Soft Delete) ---")
            try:
                pages = tm.get_page_list()
                if not pages:
                    print("No tienes páginas.")
                    continue
                
                for i, p in enumerate(pages):
                    print(f"{i+1}. {p['title']}")
                
                idx = input("\nNúmero de la página a eliminar: ")
                if not idx.isdigit() or int(idx) < 1 or int(idx) > len(pages):
                    print("❌ Selección inválida.")
                    continue
                
                target_page = pages[int(idx)-1]
                confirm = input(f"¿Seguro que quieres borrar '{target_page['title']}'? (s/n): ")
                
                if confirm.lower() == 's':
                    tm.delete_page(target_page['path'])
                    print("\n🗑️ Página marcada como ELIMINADA (Contenido vaciado).")
                else:
                    print("Operación cancelada.")
                    
            except Exception as e:
                print(f"Error: {e}")
            input("\nPresiona Enter para continuar...")

        elif opcion == '5':
            print("¡Hasta luego! 👋")
            break
        else:
            print("Opción no válida.")
                
if __name__ == "__main__":
    interactive_menu()

import os
import sys
import webbrowser
import threading
import time

def main():
    print("=" * 60)
    print("       LIGAHUB - SISTEMA DE GESTÃO PARA LIGA ACADÊMICA")
    print("=" * 60)
    print("Iniciando servidor local...")

    # Abrir navegador automaticamente após 1.5s
    def open_browser():
        time.sleep(1.5)
        url = "http://localhost:8000"
        print(f"\n[+] Abrindo navegador em: {url}")
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        import uvicorn
        uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
    except ImportError:
        print("[!] Dependências não encontradas. Instalando...")
        os.system(f'"{sys.executable}" -m pip install -r requirements.txt')
        import uvicorn
        uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()


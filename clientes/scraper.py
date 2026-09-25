# meu_app/scraper.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from urllib.parse import urljoin

def scrape_futebolaovivobrasil():
    """Scraping direto do site, sem API externa"""

    
    url = "https://www.futebolaovivobrasil.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # 1. Buscar a página
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        jogos = []
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        
        # 2. Encontrar a tabela principal
        tabela = soup.find('table', class_='tablaPrincipal')
        if not tabela:
            # Tenta encontrar por atributo
            tabela = soup.find('table', {'class': lambda x: x and 'tabla' in x})
        
        if not tabela:

            return []
        
        # 3. Processar linhas
        linhas = tabela.find_all('tr')
        current_campeonato = ""
        
        for linha in linhas:
            # Pula linha vazia
            if not linha.text.strip():
                continue
            
            # Linha de data
            if 'cabeceraTabla' in linha.get('class', []):
                data_site = linha.get_text(strip=True)
                continue
            
            # Linha de campeonato
            if 'cabeceraCompericion' in linha.get('class', []):
                # Extrai nome do campeonato
                link = linha.find('a', class_='internalLink')
                if link:
                    current_campeonato = link.get_text(strip=True)
                continue
            
            # Linha de jogo
            celula_hora = linha.find('td', class_='hora')
            if celula_hora:
                try:
                    # Hora
                    horario = celula_hora.get_text(strip=True)
                    
                    # Times e logos
                    time_mandante = "A definir"
                    logo_mandante = None
                    time_visitante = "A definir"
                    logo_visitante = None
                    
                    celula_local = linha.find('td', class_='local')
                    if celula_local:
                        # Nome do time
                        span_local = celula_local.find('span')
                        if span_local:
                            time_mandante = span_local.get_text(strip=True)
                        
                        # Logo
                        img_local = celula_local.find('img')
                        if img_local and img_local.get('src'):
                            logo_mandante = urljoin(url, img_local['src'])
                    
                    celula_visitante = linha.find('td', class_='visitante')
                    if celula_visitante:
                        # Nome do time
                        span_visitante = celula_visitante.find('span')
                        if span_visitante:
                            time_visitante = span_visitante.get_text(strip=True)
                        
                        # Logo
                        img_visitante = celula_visitante.find('img')
                        if img_visitante and img_visitante.get('src'):
                            logo_visitante = urljoin(url, img_visitante['src'])
                    
                    # Canais
                    canais = []
                    celula_canais = linha.find('td', class_='canales')
                    if celula_canais:
                        lista_canais = celula_canais.find('ul', class_='listaCanales')
                        if lista_canais:
                            for item in lista_canais.find_all('li'):
                                # Tenta pegar o título ou texto
                                nome_canal = item.get('title') or item.get_text(strip=True)
                                if nome_canal and nome_canal not in canais:
                                    canais.append(nome_canal)
                    
                    # Verifica se é evento (sorteio)
                    if 'Sorteio' in linha.get_text():
                        time_mandante = "Sorteio"
                        time_visitante = ""
                    
                    jogos.append({
                        "campeonato": current_campeonato or "Vários",
                        "time_casa": time_mandante,
                        "time_fora": time_visitante,
                        "img_casa": logo_mandante,
                        "img_fora": logo_visitante,
                        "horario": horario,
                        "status": "agendado",  # Sem status no site
                        "canais": canais,
                        "fonte": "futebolaovivobrasil.com",
                        "tem_canais": bool(canais),
                        "tem_placar_real": False
                    })
                    
                except Exception as e:

                    continue
        

        return jogos
        
    except Exception as e:

        return []

def get_jogos_fallback():
    """Fallback caso o scraping falhe"""

    
    imagens = {
        "flamengo": "https://logodetimes.com/times/flamengo/logo-flamengo-512.png",
        "corinthians": "https://logodetimes.com/times/corinthians/logo-corinthians-512.png",
    }
    
    return [
        {
            "campeonato": "COPA LIBERTADORES",
            "time_casa": "Flamengo",
            "time_fora": "Corinthians",
            "img_casa": imagens["flamengo"],
            "img_fora": imagens["corinthians"],
            "horario": "21:00",
            "status": "agendado",
            "canais": ["SporTV", "Premiere"],
            "fonte": "Exemplo",
            "tem_canais": True,
            "tem_placar_real": False
        }
    ]
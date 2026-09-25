# clientes/services.py - VERSÃO LIMPA
from django.contrib.auth import get_user_model
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from unidecode import unidecode
import re
import time
from django.core.cache import cache
from django.contrib.auth import get_user_model



User = get_user_model()

def criar_revenda(username, email, senha):
    revenda = User.objects.create_user(
        username=username,
        email=email,
        password=senha,
        tipo_usuario='revenda'  # Define o tipo de usuário como 'revenda'
    )
    return revenda




# services.py - VERSÃO LOCAL SIMPLES
from datetime import datetime
from django.core.cache import cache
from .scraper import scrape_futebolaovivobrasil, get_jogos_fallback

def buscar_jogos_do_dia():
    """Faz scraping direto, sem API externa"""

    
    # Cache por 1 hora (ajuste conforme necessidade)
    cache_key = f'jogos_scraped_{datetime.now().strftime("%Y%m%d%H")}'
    jogos_cache = cache.get(cache_key)
    
    if jogos_cache is not None:

        return jogos_cache
    
    # Faz scraping direto
    jogos = scrape_futebolaovivobrasil()
    
    # Se falhar, usa fallback
    if not jogos:

        jogos = get_jogos_fallback()
    
    # Salva no cache
    cache.set(cache_key, jogos, 3600)  # 1 hora
    

    return jogos



def get_fallback():
    """Fallback mínimo caso a API falhe"""

    return [
        {
            "campeonato": "API Indisponível",
            "time_casa": "Tente novamente",
            "time_fora": "em alguns instantes",
            "img_casa": None,
            "img_fora": None,
            "placar_casa": None,
            "placar_fora": None,
            "horario": datetime.now().strftime("%H:%M"),
            "status": "agendado",
            "canais": ["Recarregue a página"],
            "fonte": "Fallback",
            "tem_canais": True,
            "tem_placar_real": False
        }
    ]


from collections import defaultdict

def agrupar_por_campeonato(jogos):
    campeonatos = defaultdict(list)

    for jogo in jogos:
        nome = jogo.get("campeonato", "Outros")
        campeonatos[nome].append(jogo)

    return dict(campeonatos)





# clientes/services.py - VERSÃO ATUALIZADA

from django.contrib.auth import get_user_model
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime
from unidecode import unidecode
import re
import time
from django.core.cache import cache
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# ==========================================
# FUNÇÕES DE REVENDA
# ==========================================
def criar_revenda(username, email, senha):
    revenda = User.objects.create_user(
        username=username,
        email=email,
        password=senha,
        tipo_usuario='revenda'
    )
    return revenda

# ==========================================
# FUNÇÕES DE JOGOS
# ==========================================
def buscar_jogos_do_dia():
    """Faz scraping direto, sem API externa"""

    
    cache_key = f'jogos_scraped_{datetime.now().strftime("%Y%m%d%H")}'
    jogos_cache = cache.get(cache_key)
    
    if jogos_cache is not None:

        return jogos_cache
    
    jogos = scrape_futebolaovivobrasil()
    
    if not jogos:

        jogos = get_jogos_fallback()
    
    cache.set(cache_key, jogos, 3600)
    

    return jogos

def get_fallback():
    """Fallback mínimo caso a API falhe"""

    return [
        {
            "campeonato": "API Indisponível",
            "time_casa": "Tente novamente",
            "time_fora": "em alguns instantes",
            "img_casa": None,
            "img_fora": None,
            "placar_casa": None,
            "placar_fora": None,
            "horario": datetime.now().strftime("%H:%M"),
            "status": "agendado",
            "canais": ["Recarregue a página"],
            "fonte": "Fallback",
            "tem_canais": True,
            "tem_placar_real": False
        }
    ]

from collections import defaultdict

def agrupar_por_campeonato(jogos):
    campeonatos = defaultdict(list)
    for jogo in jogos:
        nome = jogo.get("campeonato", "Outros")
        campeonatos[nome].append(jogo)
    return dict(campeonatos)

# ==========================================
# SERVIÇO DE CRÉDITOS (NOVO)
# ==========================================
class CreditoService:
    """Serviço centralizado para gestão de créditos"""
    
    @staticmethod
    def consumir_credito_cliente(plano, cliente, quantidade=1, is_renovacao=False):
        """
        Consome crédito do plano para o cliente.
        Retorna: (sucesso, mensagem, custo_real)
        """
        if not plano:
            return True, None, Decimal('0.00')
        
        # Plano sem controle de estoque - usa custo cadastrado
        if not plano.controlar_estoque:
            custo = plano.custos if plano.custos else Decimal('0.00')
            return True, None, custo
        
        # Plano com controle apenas por vagas (não por créditos)
        if plano.tipo_estoque not in ['creditos', 'ambos']:
            custo = plano.custos if plano.custos else Decimal('0.00')
            return True, None, custo
        
        # Plano com controle de créditos - consome do lote
        try:
            if not plano.tem_vagas:
                return False, f"Plano '{plano.nome}' esgotado! Sem vagas.", Decimal('0.00')
            
            if plano.creditos_disponiveis <= 0:
                return False, f"Plano '{plano.nome}' sem créditos!", Decimal('0.00')
            
            sucesso, mensagem, custo_real = plano.consumir_credito(cliente, quantidade)
            
            if sucesso:
                logger.info(
                    f"✅ Crédito consumido | Plano: {plano.nome} | "
                    f"Cliente: {cliente.nome} | Custo: R$ {custo_real:.2f}"
                )
            
            return sucesso, mensagem, custo_real
            
        except Exception as e:
            logger.error(f"❌ Erro ao consumir crédito: {e}", exc_info=True)
            return False, f"Erro interno: {str(e)}", Decimal('0.00')
    
    @staticmethod
    def verificar_multiplicador(plano, login_externo, senha_leitura, dono, user_model):
        """
        Verifica regras de multiplicador/compartilhamento.
        Retorna: (is_adicional, total_existentes, mensagem_erro)
        """
        if not plano or not login_externo:
            return False, 0, None
        
        # Plano de usuário único
        if plano.usuario_unico:
            existe = user_model.objects.filter(
                login_externo=login_externo,
                plano=plano,
                is_active=True,
                dono=dono
            ).exists()
            
            if existe:
                return False, 1, f"❌ Plano '{plano.nome}' não permite compartilhamento!"
            return False, 0, None
        
        # Plano com multiplicador
        if plano.multiplicador > 1:
            filtros = {
                'login_externo': login_externo,
                'plano': plano,
                'is_active': True,
                'dono': dono
            }
            
            if senha_leitura:
                filtros['senha_leitura'] = senha_leitura
            
            existentes = user_model.objects.filter(**filtros)
            total = existentes.count()
            
            if total >= plano.multiplicador:
                return False, total, (
                    f"❌ Limite de {plano.multiplicador} usuários atingido!"
                )
            
            return total > 0, total, None
        
        return False, 0, None
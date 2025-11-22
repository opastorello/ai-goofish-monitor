import asyncio
import json
import math
import os
import random
import re
from datetime import datetime
from functools import wraps
from urllib.parse import quote

from openai import APIStatusError
from requests.exceptions import HTTPError


def retry_on_failure(retries=3, delay=5):
    """
    Um decorador de retry assíncrono genérico com registros detalhados para erros HTTP.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except (APIStatusError, HTTPError) as e:
                    print(f"Função {func.__name__} falhou na tentativa {i + 1}/{retries} com erro HTTP.")
                    if hasattr(e, 'status_code'):
                        print(f"  - Código de status: {e.status_code}")
                    if hasattr(e, 'response') and hasattr(e.response, 'text'):
                        response_text = e.response.text
                        print(
                            f"  - Resposta: {response_text[:300]}{'...' if len(response_text) > 300 else ''}")
                except json.JSONDecodeError as e:
                    print(f"Função {func.__name__} falhou na tentativa {i + 1}/{retries}: erro ao analisar JSON - {e}")
                except Exception as e:
                    print(f"Função {func.__name__} falhou na tentativa {i + 1}/{retries}: {type(e).__name__} - {e}")

                if i < retries - 1:
                    print(f"Tentando novamente em {delay} segundos...")
                    await asyncio.sleep(delay)

            print(f"Função {func.__name__} falhou completamente após {retries} tentativas.")
            return None
        return wrapper
    return decorator


async def safe_get(data, *keys, default="N/A"):
    """Obtém valores de dicionários aninhados com segurança."""
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data


async def random_sleep(min_seconds: float, max_seconds: float):
    """Aguarda de forma assíncrona um tempo aleatório dentro do intervalo fornecido."""
    delay = random.uniform(min_seconds, max_seconds)
    print(f"   [Atraso] Esperando {delay:.2f} segundos... (intervalo: {min_seconds}-{max_seconds}s)")
    await asyncio.sleep(delay)


def log_time(message: str, prefix: str = "") -> None:
    """Registra mensagens com timestamp no formato YY-MM-DD HH:MM:SS."""
    try:
        ts = datetime.now().strftime(' %Y-%m-%d %H:%M:%S')
    except Exception:
        ts = "--:--:--"
    print(f"[{ts}] {prefix}{message}")


def convert_goofish_link(url: str) -> str:
    """
    Converte um link de produto do Goofish para o formato móvel contendo apenas o ID.
    """
    match_first_link = re.search(r'item\?id=(\d+)', url)
    if match_first_link:
        item_id = match_first_link.group(1)
        bfp_json = f'{{"id":{item_id}}}'
        return f"https://pages.goofish.com/sharexy?loadingVisible=false&bft=item&bfs=idlepc.item&spm=a21ybx.item.0.0&bfp={quote(bfp_json)}"
    return url


def get_link_unique_key(link: str) -> str:
    """Usa o conteúdo antes do primeiro "&" como chave única do link."""
    return link.split('&', 1)[0]


async def save_to_jsonl(data_record: dict, keyword: str):
    """Acrescenta um registro completo de produto e vendedor a um arquivo .jsonl."""
    output_dir = "jsonl"
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f"{keyword.replace(' ', '_')}_full_data.jsonl")
    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(data_record, ensure_ascii=False) + "\n")
        return True
    except IOError as e:
        print(f"Erro ao gravar o arquivo {filename}: {e}")
        return False


def format_registration_days(total_days: int) -> str:
    """
    Formata o total de dias em uma string “X anos Y meses”.
    """
    if not isinstance(total_days, int) or total_days <= 0:
        return 'Desconhecido'

    DAYS_IN_YEAR = 365.25
    DAYS_IN_MONTH = DAYS_IN_YEAR / 12

    years = math.floor(total_days / DAYS_IN_YEAR)
    remaining_days = total_days - (years * DAYS_IN_YEAR)
    months = round(remaining_days / DAYS_IN_MONTH)

    if months == 12:
        years += 1
        months = 0

    if years > 0 and months > 0:
        return f"Na Xianyu há {years} ano(s) e {months} mês(es)"
    elif years > 0 and months == 0:
        return f"Na Xianyu há {years} ano(s)"
    elif years == 0 and months > 0:
        return f"Na Xianyu há {months} mês(es)"
    else:
        return "Na Xianyu há menos de um mês"

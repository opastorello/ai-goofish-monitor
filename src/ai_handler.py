import asyncio
import base64
import json
import os
import re
import sys
import shutil
from datetime import datetime
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

import requests

# Define a codificação padrão de saída como UTF-8 para corrigir consoles do Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())

from src.config import (
    AI_DEBUG_MODE,
    IMAGE_DOWNLOAD_HEADERS,
    IMAGE_SAVE_DIR,
    TASK_IMAGE_DIR_PREFIX,
    MODEL_NAME,
    NTFY_TOPIC_URL,
    GOTIFY_URL,
    GOTIFY_TOKEN,
    BARK_URL,
    PCURL_TO_MOBILE,
    WX_BOT_URL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    WEBHOOK_URL,
    WEBHOOK_METHOD,
    WEBHOOK_HEADERS,
    WEBHOOK_CONTENT_TYPE,
    WEBHOOK_QUERY_PARAMETERS,
    WEBHOOK_BODY,
    ENABLE_RESPONSE_FORMAT,
    client,
)
from src.utils import convert_goofish_link, retry_on_failure


def safe_print(text):
    """Função de impressão segura que lida com erros de codificação."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Se houver erro de codificação, tenta usar ASCII ignorando caracteres inválidos
        try:
            print(text.encode('ascii', errors='ignore').decode('ascii'))
        except:
            # Se ainda falhar, imprime uma mensagem simplificada
            print("[A saída contém caracteres que não podem ser exibidos]")


@retry_on_failure(retries=2, delay=3)
async def _download_single_image(url, save_path):
    """Função interna com retry para baixar uma única imagem de forma assíncrona."""
    loop = asyncio.get_running_loop()
    # Usa run_in_executor para rodar requests síncrono sem bloquear o loop de eventos
    response = await loop.run_in_executor(
        None,
        lambda: requests.get(url, headers=IMAGE_DOWNLOAD_HEADERS, timeout=20, stream=True)
    )
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return save_path


async def download_all_images(product_id, image_urls, task_name="default"):
    """Baixa de forma assíncrona todas as imagens de um produto, pulando as que já existem. Suporta isolamento por tarefa."""
    if not image_urls:
        return []

    # Cria diretórios de imagens separados por tarefa
    task_image_dir = os.path.join(IMAGE_SAVE_DIR, f"{TASK_IMAGE_DIR_PREFIX}{task_name}")
    os.makedirs(task_image_dir, exist_ok=True)

    urls = [url.strip() for url in image_urls if url.strip().startswith('http')]
    if not urls:
        return []

    saved_paths = []
    total_images = len(urls)
    for i, url in enumerate(urls):
        try:
            clean_url = url.split('.heic')[0] if '.heic' in url else url
            file_name_base = os.path.basename(clean_url).split('?')[0]
            file_name = f"product_{product_id}_{i + 1}_{file_name_base}"
            file_name = re.sub(r'[\\/*?:"<>|]', "", file_name)
            if not os.path.splitext(file_name)[1]:
                file_name += ".jpg"

            save_path = os.path.join(task_image_dir, file_name)

            if os.path.exists(save_path):
                safe_print(f"   [Imagem] {i + 1}/{total_images} já existe, pulando download: {os.path.basename(save_path)}")
                saved_paths.append(save_path)
                continue

            safe_print(f"   [Imagem] Baixando imagem {i + 1}/{total_images}: {url}")
            if await _download_single_image(url, save_path):
                safe_print(f"   [Imagem] {i + 1}/{total_images} baixada em: {os.path.basename(save_path)}")
                saved_paths.append(save_path)
        except Exception as e:
            safe_print(f"   [Imagem] Erro ao processar {url}, imagem ignorada: {e}")

    return saved_paths


def cleanup_task_images(task_name):
    """Limpa o diretório de imagens temporárias de uma tarefa."""
    task_image_dir = os.path.join(IMAGE_SAVE_DIR, f"{TASK_IMAGE_DIR_PREFIX}{task_name}")
    if os.path.exists(task_image_dir):
        try:
            shutil.rmtree(task_image_dir)
            safe_print(f"   [Limpeza] Diretório temporário da tarefa '{task_name}' removido: {task_image_dir}")
        except Exception as e:
            safe_print(f"   [Limpeza] Erro ao excluir diretório temporário da tarefa '{task_name}': {e}")
    else:
        safe_print(f"   [Limpeza] Diretório temporário da tarefa '{task_name}' não existe: {task_image_dir}")


def encode_image_to_base64(image_path):
    """Codifica um arquivo de imagem local em Base64."""
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        safe_print(f"Erro ao codificar a imagem: {e}")
        return None


def validate_ai_response_format(parsed_response):
    """Valida se a resposta da IA está no formato esperado."""
    required_fields = [
        "prompt_version",
        "is_recommended",
        "reason",
        "risk_tags",
        "criteria_analysis"
    ]

    criteria_analysis_fields = [
        "model_chip",
        "battery_health",
        "condition",
        "history",
        "seller_type",
        "shipping",
        "seller_credit"
    ]

    seller_type_fields = [
        "status",
        "persona",
        "comment",
        "analysis_details"
    ]

    # Verifica campos de nível superior
    for field in required_fields:
        if field not in parsed_response:
            safe_print(f"   [Análise de IA] Aviso: resposta sem o campo obrigatório '{field}'")
            return False

    # Verifica o campo criteria_analysis
    criteria_analysis = parsed_response.get("criteria_analysis", {})
    for field in criteria_analysis_fields:
        if field not in criteria_analysis:
            safe_print(f"   [Análise de IA] Aviso: criteria_analysis sem o campo '{field}'")
            return False

    # Verifica analysis_details em seller_type
    seller_type = criteria_analysis.get("seller_type", {})
    if "analysis_details" in seller_type:
        analysis_details = seller_type["analysis_details"]
        required_details = ["temporal_analysis", "selling_behavior", "buying_behavior", "behavioral_summary"]
        for detail in required_details:
            if detail not in analysis_details:
                safe_print(f"   [Análise de IA] Aviso: analysis_details sem o campo '{detail}'")
                return False

    # Verifica tipos de dados
    if not isinstance(parsed_response.get("is_recommended"), bool):
        safe_print("   [Análise de IA] Aviso: o campo is_recommended não é booleano")
        return False

    if not isinstance(parsed_response.get("risk_tags"), list):
        safe_print("   [Análise de IA] Aviso: o campo risk_tags não é uma lista")
        return False

    return True


@retry_on_failure(retries=3, delay=5)
async def send_ntfy_notification(product_data, reason):
    """Envia de forma assíncrona uma notificação ntfy.sh de alta prioridade quando um item é recomendado."""
    if not NTFY_TOPIC_URL and not WX_BOT_URL and not (GOTIFY_URL and GOTIFY_TOKEN) and not BARK_URL and not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) and not WEBHOOK_URL:
        safe_print("Aviso: nenhum serviço de notificação configurado em .env (NTFY_TOPIC_URL, WX_BOT_URL, GOTIFY_URL/TOKEN, BARK_URL, TELEGRAM_BOT_TOKEN/CHAT_ID, WEBHOOK_URL). Notificação ignorada.")
        return

    title = product_data.get('商品标题', 'N/A')
    price = product_data.get('当前售价', 'N/A')
    link = product_data.get('商品链接', '#')
    if PCURL_TO_MOBILE:
        mobile_link = convert_goofish_link(link)
        message = f"Preço: {price}\nMotivo: {reason}\nLink móvel: {mobile_link}\nLink desktop: {link}"
    else:
        message = f"Preço: {price}\nMotivo: {reason}\nLink: {link}"

    notification_title = f"🚨 Nova recomendação! {title[:30]}..."

    # --- Enviar notificação ntfy ---
    if NTFY_TOPIC_URL:
        try:
            safe_print(f"   -> Enviando notificação ntfy para: {NTFY_TOPIC_URL}")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: requests.post(
                    NTFY_TOPIC_URL,
                    data=message.encode('utf-8'),
                    headers={
                        "Title": notification_title.encode('utf-8'),
                        "Priority": "urgent",
                        "Tags": "bell,vibration"
                    },
                    timeout=10
                )
            )
            safe_print("   -> Notificação ntfy enviada com sucesso.")
        except Exception as e:
            safe_print(f"   -> Falha ao enviar notificação ntfy: {e}")

    # --- Enviar notificação Gotify ---
    if GOTIFY_URL and GOTIFY_TOKEN:
        try:
            safe_print(f"   -> Enviando notificação Gotify para: {GOTIFY_URL}")
            # Gotify uses multipart/form-data
            payload = {
                'title': (None, notification_title),
                'message': (None, message),
                'priority': (None, '5')
            }

            gotify_url_with_token = f"{GOTIFY_URL}/message?token={GOTIFY_TOKEN}"

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    gotify_url_with_token,
                    files=payload,
                    timeout=10
                )
            )
            response.raise_for_status()
            safe_print("   -> Notificação Gotify enviada com sucesso.")
        except requests.exceptions.RequestException as e:
            safe_print(f"   -> Falha ao enviar notificação Gotify: {e}")
        except Exception as e:
            safe_print(f"   -> Erro desconhecido ao enviar notificação Gotify: {e}")

    # --- Enviar notificação Bark ---
    if BARK_URL:
        try:
            safe_print(f"   -> Enviando notificação Bark...")

            bark_payload = {
                "title": notification_title,
                "body": message,
                "level": "timeSensitive",
                "group": "Monitoramento Xianyu"
            }

            link_to_use = convert_goofish_link(link) if PCURL_TO_MOBILE else link
            bark_payload["url"] = link_to_use

            # Add icon if available
            main_image = product_data.get('商品主图链接')
            if not main_image:
                # Fallback to image list if main image not present
                image_list = product_data.get('商品图片列表', [])
                if image_list:
                    main_image = image_list[0]

            if main_image:
                bark_payload['icon'] = main_image

            headers = { "Content-Type": "application/json; charset=utf-8" }
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    BARK_URL,
                    json=bark_payload,
                    headers=headers,
                    timeout=10
                )
            )
            response.raise_for_status()
            safe_print("   -> Notificação Bark enviada com sucesso.")
        except requests.exceptions.RequestException as e:
            safe_print(f"   -> Falha ao enviar notificação Bark: {e}")
        except Exception as e:
            safe_print(f"   -> Erro desconhecido ao enviar notificação Bark: {e}")

    # --- Enviar notificação via robô WeCom ---
    if WX_BOT_URL:
        # Converte mensagem para Markdown para links clicáveis
        lines = message.split('\n')
        markdown_content = f"## {notification_title}\n\n"

        for line in lines:
            if line.startswith('Link móvel:') or line.startswith('Link desktop:') or line.startswith('Link:'):
                # Extrai a parte do link e converte para hiperlink Markdown
                if ':' in line:
                    label, url = line.split(':', 1)
                    url = url.strip()
                    if url and url != '#':
                        markdown_content += f"- **{label}:** [{url}]({url})\n"
                    else:
                        markdown_content += f"- **{label}:** Link indisponível\n"
                else:
                    markdown_content += f"- {line}\n"
            else:
                # Mantém as demais linhas
                if line:
                    markdown_content += f"- {line}\n"
                else:
                    markdown_content += "\n"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content
            }
        }

        try:
            safe_print(f"   -> Enviando notificação do WeCom para: {WX_BOT_URL}")
            headers = { "Content-Type": "application/json" }
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    WX_BOT_URL,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
            )
            response.raise_for_status()
            result = response.json()
            safe_print(f"   -> Notificação WeCom enviada com sucesso. Resposta: {result}")
        except requests.exceptions.RequestException as e:
            safe_print(f"   -> Falha ao enviar notificação WeCom: {e}")
        except Exception as e:
            safe_print(f"   -> Erro desconhecido ao enviar notificação WeCom: {e}")

    # --- Enviar notificação via bot do Telegram ---
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            safe_print(f"   -> Enviando notificação do Telegram...")
            
            # Monta a URL da API do Telegram
            telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

            # Formata o conteúdo da mensagem
            telegram_message = f"🚨 <b>Nova recomendação!</b>\n\n"
            telegram_message += f"<b>{title[:50]}...</b>\n\n"
            telegram_message += f"💰 Preço: {price}\n"
            telegram_message += f"📝 Motivo: {reason}\n"

            # Adiciona links
            if PCURL_TO_MOBILE:
                mobile_link = convert_goofish_link(link)
                telegram_message += f"📱 <a href='{mobile_link}'>Link móvel</a>\n"
            telegram_message += f"💻 <a href='{link}'>Link desktop</a>"
            
            # Monta o payload da requisição
            telegram_payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": telegram_message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            }
            
            headers = {"Content-Type": "application/json"}
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    telegram_api_url,
                    json=telegram_payload,
                    headers=headers,
                    timeout=10
                )
            )
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                safe_print("   -> Notificação do Telegram enviada com sucesso.")
            else:
                safe_print(f"   -> Falha ao enviar notificação do Telegram: {result.get('description', 'Erro desconhecido')}")
        except requests.exceptions.RequestException as e:
            safe_print(f"   -> Falha ao enviar notificação do Telegram: {e}")
        except Exception as e:
            safe_print(f"   -> Erro desconhecido ao enviar notificação do Telegram: {e}")

    # --- Enviar notificação Webhook genérica ---
    if WEBHOOK_URL:
        try:
            safe_print(f"   -> Enviando notificação Webhook para: {WEBHOOK_URL}")

            # Substitui variáveis
            def replace_placeholders(template_str):
                if not template_str:
                    return ""
                # Escapa conteúdo em JSON para evitar quebras de linha e caracteres especiais
                safe_title = json.dumps(notification_title, ensure_ascii=False)[1:-1]  # remove aspas externas
                safe_content = json.dumps(message, ensure_ascii=False)[1:-1]  # remove aspas externas
                # Suporta formatos antigos ${title}${content} e novos {{title}}{{content}}
                return template_str.replace("${title}", safe_title).replace("${content}", safe_content).replace("{{title}}", safe_title).replace("{{content}}", safe_content)

            # Prepara cabeçalhos
            headers = {}
            if WEBHOOK_HEADERS:
                try:
                    headers = json.loads(WEBHOOK_HEADERS)
                except json.JSONDecodeError:
                    safe_print(f"   -> [Aviso] Cabeçalhos do Webhook em formato incorreto; verifique WEBHOOK_HEADERS no .env.")

            loop = asyncio.get_running_loop()

            if WEBHOOK_METHOD == "GET":
                # Prepara parâmetros de consulta
                final_url = WEBHOOK_URL
                if WEBHOOK_QUERY_PARAMETERS:
                    try:
                        params_str = replace_placeholders(WEBHOOK_QUERY_PARAMETERS)
                        params = json.loads(params_str)

                        # Analisa a URL original e anexa novos parâmetros
                        url_parts = list(urlparse(final_url))
                        query = dict(parse_qsl(url_parts[4]))
                        query.update(params)
                        url_parts[4] = urlencode(query)
                        final_url = urlunparse(url_parts)
                    except json.JSONDecodeError:
                        safe_print(f"   -> [Aviso] Parâmetros de consulta do Webhook em formato incorreto; verifique WEBHOOK_QUERY_PARAMETERS no .env.")

                response = await loop.run_in_executor(
                    None,
                    lambda: requests.get(final_url, headers=headers, timeout=15)
                )

            elif WEBHOOK_METHOD == "POST":
                # Prepara corpo da requisição
                data = None
                json_payload = None

                if WEBHOOK_BODY:
                    body_str = replace_placeholders(WEBHOOK_BODY)
                    try:
                        if WEBHOOK_CONTENT_TYPE == "JSON":
                            json_payload = json.loads(body_str)
                            if 'Content-Type' not in headers and 'content-type' not in headers:
                                headers['Content-Type'] = 'application/json; charset=utf-8'
                        elif WEBHOOK_CONTENT_TYPE == "FORM":
                            data = json.loads(body_str)  # requests lida com url-encoding
                            if 'Content-Type' not in headers and 'content-type' not in headers:
                                headers['Content-Type'] = 'application/x-www-form-urlencoded'
                        else:
                            safe_print(f"   -> [Aviso] WEBHOOK_CONTENT_TYPE não suportado: {WEBHOOK_CONTENT_TYPE}.")
                    except json.JSONDecodeError:
                        safe_print(f"   -> [Aviso] Corpo do Webhook em formato incorreto; verifique WEBHOOK_BODY no .env.")

                response = await loop.run_in_executor(
                    None,
                    lambda: requests.post(WEBHOOK_URL, headers=headers, json=json_payload, data=data, timeout=15)
                )
            else:
                safe_print(f"   -> [Aviso] WEBHOOK_METHOD não suportado: {WEBHOOK_METHOD}.")
                return

            response.raise_for_status()
            safe_print(f"   -> Notificação Webhook enviada com sucesso. Status: {response.status_code}")

        except requests.exceptions.RequestException as e:
            safe_print(f"   -> Falha ao enviar notificação Webhook: {e}")
        except Exception as e:
            safe_print(f"   -> Erro desconhecido ao enviar notificação Webhook: {e}")


@retry_on_failure(retries=3, delay=5)
async def get_ai_analysis(product_data, image_paths=None, prompt_text=""):
    """Envia o JSON completo do produto e imagens para a IA analisar (assíncrono)."""
    if not client:
        safe_print("   [Análise de IA] Erro: cliente de IA não inicializado, pulando análise.")
        return None

    item_info = product_data.get('商品信息', {})
    product_id = item_info.get('商品ID', 'N/A')

    safe_print(f"\n   [Análise de IA] Iniciando análise do produto #{product_id} (incluindo {len(image_paths or [])} imagem(ns))...")
    safe_print(f"   [Análise de IA] Título: {item_info.get('商品标题', 'N/A')}")

    if not prompt_text:
        safe_print("   [Análise de IA] Erro: prompt necessário para análise não fornecido.")
        return None

    product_details_json = json.dumps(product_data, ensure_ascii=False, indent=2)
    system_prompt = prompt_text

    if AI_DEBUG_MODE:
        safe_print("\n--- [AI DEBUG] ---")
        safe_print("--- DADOS DO PRODUTO (JSON) ---")
        safe_print(product_details_json)
        safe_print("--- TEXTO DO PROMPT (completo) ---")
        safe_print(prompt_text)
        safe_print("-------------------\n")

    combined_text_prompt = f"""Por favor, com base em seu conhecimento e nas minhas instruções, analise o JSON completo do produto abaixo:

```json
    {product_details_json}
```

{system_prompt}
"""
    user_content_list = []

    # Primeiro adiciona o conteúdo das imagens
    if image_paths:
        for path in image_paths:
            base64_image = encode_image_to_base64(path)
            if base64_image:
                user_content_list.append(
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})

    # Depois adiciona o conteúdo de texto
    user_content_list.append({"type": "text", "text": combined_text_prompt})

    messages = [{"role": "user", "content": user_content_list}]

    # Salva o conteúdo enviado em um arquivo de log
    try:
        # Cria pasta logs
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)

        # Gera nome do arquivo (timestamp atual)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{current_time}.log"
        log_filepath = os.path.join(logs_dir, log_filename)

        # Prepara conteúdo do log - salva a carga original
        log_content = json.dumps(messages, ensure_ascii=False)

        # Escreve no arquivo
        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write(log_content)

        safe_print(f"   [Log] Solicitação de análise de IA salva em: {log_filepath}")

    except Exception as e:
        safe_print(f"   [Log] Erro ao salvar log da análise de IA: {e}")

    # Chamada de IA aprimorada com controle de formato e tentativas
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Ajusta parâmetros conforme a tentativa
            current_temperature = 0.1 if attempt == 0 else 0.05  # Temperatura menor em novas tentativas

            from src.config import get_ai_request_params
            
            # Monta parâmetros e decide response_format conforme ENABLE_RESPONSE_FORMAT
            request_params = {
                "model": MODEL_NAME,
                "messages": messages,
                "temperature": current_temperature,
                "max_tokens": 4000
            }

            # Adiciona response_format apenas se habilitado
            if ENABLE_RESPONSE_FORMAT:
                request_params["response_format"] = {"type": "json_object"}
            
            response = await client.chat.completions.create(
                **get_ai_request_params(**request_params)
            )

            ai_response_content = response.choices[0].message.content

            if AI_DEBUG_MODE:
                safe_print(f"\n--- [AI DEBUG] Tentativa {attempt + 1} ---")
                safe_print("--- RESPOSTA DA IA (bruta) ---")
                safe_print(ai_response_content)
                safe_print("---------------------\n")

            # Tenta analisar o JSON diretamente
            try:
                parsed_response = json.loads(ai_response_content)

                # Valida o formato da resposta
                if validate_ai_response_format(parsed_response):
                    safe_print(f"   [Análise de IA] Tentativa {attempt + 1} bem-sucedida; formato validado")
                    return parsed_response
                else:
                    safe_print(f"   [Análise de IA] Tentativa {attempt + 1} falhou na validação de formato")
                    if attempt < max_retries - 1:
                        safe_print(f"   [Análise de IA] Preparando tentativa {attempt + 2}...")
                        continue
                    else:
                        safe_print("   [Análise de IA] Todas as tentativas concluídas; usando o último resultado")
                        return parsed_response

            except json.JSONDecodeError:
                safe_print(f"   [Análise de IA] Tentativa {attempt + 1} falhou ao analisar JSON, tentando limpar a resposta...")

                # Remove possíveis marcadores de bloco de código Markdown
                cleaned_content = ai_response_content.strip()
                if cleaned_content.startswith('```json'):
                    cleaned_content = cleaned_content[7:]
                if cleaned_content.startswith('```'):
                    cleaned_content = cleaned_content[3:]
                if cleaned_content.endswith('```'):
                    cleaned_content = cleaned_content[:-3]
                cleaned_content = cleaned_content.strip()

                # Procura limites do objeto JSON
                json_start_index = cleaned_content.find('{')
                json_end_index = cleaned_content.rfind('}')

                if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
                    json_str = cleaned_content[json_start_index:json_end_index + 1]
                    try:
                        parsed_response = json.loads(json_str)
                        if validate_ai_response_format(parsed_response):
                            safe_print(f"   [Análise de IA] Tentativa {attempt + 1} bem-sucedida após limpeza")
                            return parsed_response
                        else:
                            if attempt < max_retries - 1:
                                safe_print(f"   [Análise de IA] Preparando tentativa {attempt + 2}...")
                                continue
                            else:
                                safe_print("   [Análise de IA] Todas as tentativas concluídas; usando resultado limpo")
                                return parsed_response
                    except json.JSONDecodeError as e:
                        safe_print(f"   [Análise de IA] Tentativa {attempt + 1} ainda falhou ao analisar JSON após limpeza: {e}")
                        if attempt < max_retries - 1:
                            safe_print(f"   [Análise de IA] Preparando tentativa {attempt + 2}...")
                            continue
                        else:
                            raise e
                else:
                    safe_print(f"   [Análise de IA] Tentativa {attempt + 1} não encontrou JSON válido na resposta")
                    if attempt < max_retries - 1:
                        safe_print(f"   [Análise de IA] Preparando tentativa {attempt + 2}...")
                        continue
                    else:
                        raise json.JSONDecodeError("No valid JSON object found", ai_response_content, 0)

        except Exception as e:
            safe_print(f"   [Análise de IA] Tentativa {attempt + 1} falhou ao chamar a IA: {e}")
            if attempt < max_retries - 1:
                safe_print(f"   [Análise de IA] Preparando tentativa {attempt + 2}...")
                continue
            else:
                raise e

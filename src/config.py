import os
import sys

from dotenv import load_dotenv
from openai import AsyncOpenAI

# --- AI & Notification Configuration ---
load_dotenv()

# --- File Paths & Directories ---
STATE_FILE = "xianyu_state.json"
IMAGE_SAVE_DIR = "images"
CONFIG_FILE = "config.json"
os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

# Prefixo para diretórios temporários de imagens isolados por tarefa
TASK_IMAGE_DIR_PREFIX = "task_images_"

# --- API URL Patterns ---
API_URL_PATTERN = "h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search"
DETAIL_API_URL_PATTERN = "h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail"

# --- Environment Variables ---
API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL")
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")
PROXY_URL = os.getenv("PROXY_URL")
NTFY_TOPIC_URL = os.getenv("NTFY_TOPIC_URL")
GOTIFY_URL = os.getenv("GOTIFY_URL")
GOTIFY_TOKEN = os.getenv("GOTIFY_TOKEN")
BARK_URL = os.getenv("BARK_URL")
WX_BOT_URL = os.getenv("WX_BOT_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_METHOD = os.getenv("WEBHOOK_METHOD", "POST").upper()
WEBHOOK_HEADERS = os.getenv("WEBHOOK_HEADERS")
WEBHOOK_CONTENT_TYPE = os.getenv("WEBHOOK_CONTENT_TYPE", "JSON").upper()
WEBHOOK_QUERY_PARAMETERS = os.getenv("WEBHOOK_QUERY_PARAMETERS")
WEBHOOK_BODY = os.getenv("WEBHOOK_BODY")
PCURL_TO_MOBILE = os.getenv("PCURL_TO_MOBILE", "false").lower() == "true"
RUN_HEADLESS = os.getenv("RUN_HEADLESS", "true").lower() != "false"
LOGIN_IS_EDGE = os.getenv("LOGIN_IS_EDGE", "false").lower() == "true"
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
AI_DEBUG_MODE = os.getenv("AI_DEBUG_MODE", "false").lower() == "true"
SKIP_AI_ANALYSIS = os.getenv("SKIP_AI_ANALYSIS", "false").lower() == "true"
ENABLE_THINKING = os.getenv("ENABLE_THINKING", "false").lower() == "true"
ENABLE_RESPONSE_FORMAT = os.getenv("ENABLE_RESPONSE_FORMAT", "true").lower() == "true"

# --- Headers ---
IMAGE_DOWNLOAD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# --- Client Initialization ---
# Verifica se a configuração está completa
if not all([BASE_URL, MODEL_NAME]):
    print("Aviso: OPENAI_BASE_URL e OPENAI_MODEL_NAME não estão totalmente definidos no .env. Os recursos de IA podem não funcionar.")
    client = None
else:
    try:
        if PROXY_URL:
            print(f"Usando proxy HTTP/S para requisições de IA: {PROXY_URL}")
            # httpx lê as configurações de proxy das variáveis de ambiente
            os.environ['HTTP_PROXY'] = PROXY_URL
            os.environ['HTTPS_PROXY'] = PROXY_URL

        # O httpx interno do cliente openai obtém o proxy das variáveis de ambiente
        client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    except Exception as e:
        print(f"Erro ao inicializar o cliente OpenAI: {e}")
        client = None

# Verifica se o cliente de IA foi inicializado com sucesso
if not client:
    # Em prompt_generator.py, se client for None, haverá erro e saída imediata
    # Em spider_v2.py, a análise de IA será ignorada
    # Para consistência, apenas registramos o aviso aqui; a lógica é tratada pelos chamadores
    pass

# Verifica as configurações essenciais
if not all([BASE_URL, MODEL_NAME]) and 'prompt_generator.py' in sys.argv[0]:
    sys.exit("Erro: defina OPENAI_BASE_URL e OPENAI_MODEL_NAME no arquivo .env. (OPENAI_API_KEY é opcional para alguns serviços)")

def get_ai_request_params(**kwargs):
    """
    Monta os parâmetros da requisição de IA, adicionando campos conforme ENABLE_THINKING e ENABLE_RESPONSE_FORMAT
    """
    if ENABLE_THINKING:
        kwargs["extra_body"] = {"enable_thinking": False}
    
    # Remove response_format se estiver desativado
    if not ENABLE_RESPONSE_FORMAT and "response_format" in kwargs:
        del kwargs["response_format"]
    
    return kwargs

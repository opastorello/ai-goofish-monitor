# Robô Inteligente de Monitoramento do Goofish (Xianyu)

Uma ferramenta de monitoramento em tempo real e análise inteligente para o Goofish (Xianyu) baseada em Playwright e filtragem com IA, com uma interface Web completa.

## ✨ Destaques do Projeto

- **Interface Web visual**: UI completa para gerenciamento visual das tarefas, edição online dos critérios de IA, visualização em tempo real dos logs de execução e navegação pelos resultados filtrados. Não é preciso mexer diretamente em linha de comando ou arquivos de configuração.
- **Criação de tarefas guiada por IA**: Basta descrever em linguagem natural o que você quer comprar para criar, em um clique, uma nova tarefa com regras complexas de filtragem.
- **Múltiplas tarefas em paralelo**: Monitore vários termos no `config.json` ao mesmo tempo; cada tarefa roda de forma independente.
- **Processamento em fluxo em tempo real**: Assim que um novo item é encontrado, ele entra imediatamente no fluxo de análise — nada de esperar por lotes.
- **Análise profunda com IA**: Integra modelos multimodais (como GPT-4o), combinando texto, imagens e perfil do vendedor para filtrar com precisão.
- **Altamente customizável**: Cada tarefa pode ter palavras-chave, faixa de preço, filtros e instruções de IA (Prompt) próprios.
- **Notificações instantâneas**: Envie itens recomendados direto para o seu celular ou desktop via [ntfy.sh](https://ntfy.sh/), robô do WeChat Empresarial ou [Bark](https://bark.day.app/).
- **Agendamento com cron**: Defina expressões Cron para dar horários diferentes a cada tarefa.
- **Deploy em um comando com Docker**: `docker-compose` incluído para uma implantação containerizada rápida e padronizada.
- **Estratégias robustas contra anti-scraping**: Simula ações humanas com atrasos aleatórios e gestos de usuário para melhorar a estabilidade.

## Capturas de Tela

**Gestão de Tarefas no Painel**
![img.png](static/img.png)

**Visão do Monitoramento**
![img_1.png](static/img_1.png)

**Notificações via ntfy**
![img_2.png](static/img_2.png)

## 🚀 Guia Rápido (recomendado usar o Web UI)

Recomendamos operar o projeto pela interface Web para a melhor experiência.

### Passo 1: Preparar o ambiente

> ⚠️ **Versão do Python**: Para executar localmente, use Python 3.10 ou superior. Versões mais antigas podem falhar na instalação de dependências ou gerar erros em tempo de execução (por exemplo, `ModuleNotFoundError: No module named 'PIL'`).

Clone o projeto:

```bash
git clone https://github.com/opastorello/ai-goofish-monitor
cd ai-goofish-monitor
```

Crie e ative um ambiente virtual (recomendado):

```bash
python -m venv .venv
source .venv/bin/activate
```

No Windows, use:

```cmd
.venv\\Scripts\\activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### Passo 2: Configuração básica

1. **Configurar variáveis de ambiente**: copie `.env.example` para `.env` e ajuste os valores.

    No Windows:

    ```cmd
    copy .env.example .env
    ```

    No Linux/MacOS:

    ```shell
    cp .env.example .env
    ```

    Todas as opções disponíveis em `.env`:

    | Variável | Descrição | Obrigatório | Observações |
    | :--- | :--- | :--- | :--- |
    | `OPENAI_API_KEY` | API Key fornecida pelo provedor do seu modelo de IA. | Sim | Para alguns serviços locais ou proxys específicos pode ser opcional. |
    | `OPENAI_BASE_URL` | Endpoint da API compatível com o formato OpenAI. | Sim | Use o caminho base, por exemplo `https://ark.cn-beijing.volces.com/api/v3/`. |
    | `OPENAI_MODEL_NAME` | Nome do modelo que será usado. | Sim | **Precisa** ser um modelo multimodal com suporte a imagens, como `doubao-seed-1-6-250615`, `gemini-2.5-pro` etc. |
    | `PROXY_URL` | (Opcional) Proxy HTTP/S para acessar a internet. | Não | Suporta `http://` e `socks5://`, ex.: `http://127.0.0.1:7890`. |
    | `NTFY_TOPIC_URL` | (Opcional) URL do tópico no [ntfy.sh](https://ntfy.sh/) para notificações. | Não | Deixe em branco para desativar. |
    | `GOTIFY_URL` | (Opcional) Endereço do seu servidor Gotify. | Não | Ex.: `https://push.example.de`. |
    | `GOTIFY_TOKEN` | (Opcional) Token do aplicativo Gotify. | Não |  |
    | `BARK_URL` | (Opcional) Endpoint do [Bark](https://bark.day.app/). | Não | Ex.: `https://api.day.app/your_key`. Deixe em branco para desativar. |
    | `WX_BOT_URL` | (Opcional) Webhook do robô de WeChat Empresarial. | Não | Coloque o valor entre aspas no `.env` para evitar erro de parsing. |
    | `WEBHOOK_URL` | (Opcional) URL de um Webhook genérico. | Não | Deixe em branco para desativar. |
    | `WEBHOOK_METHOD` | (Opcional) Método do Webhook. | Não | `GET` ou `POST`, padrão `POST`. |
    | `WEBHOOK_HEADERS` | (Opcional) Cabeçalhos personalizados para o Webhook. | Não | Deve ser uma string JSON válida, ex.: `'{"Authorization": "Bearer xxx"}'`. |
    | `WEBHOOK_CONTENT_TYPE` | (Opcional) Content-Type para requisições POST. | Não | `JSON` ou `FORM`, padrão `JSON`. |
    | `WEBHOOK_QUERY_PARAMETERS` | (Opcional) Parâmetros de query em requisições GET. | Não | String JSON; suporta placeholders `{{title}}` e `{{content}}`. |
    | `WEBHOOK_BODY` | (Opcional) Corpo do POST. | Não | String JSON; suporta placeholders `{{title}}` e `{{content}}`. |
    | `LOGIN_IS_EDGE` | Usar Edge para login e scraping. | Não | Padrão `false` (Chrome/Chromium). |
    | `PCURL_TO_MOBILE` | Converter links desktop para versão mobile nas notificações. | Não | Padrão `true`. |
    | `RUN_HEADLESS` | Executar navegador em modo headless. | Não | Padrão `true`. Para depurar captcha localmente, defina `false`. **No Docker deve ser `true`.** |
    | `AI_DEBUG_MODE` | Habilitar modo de depuração da IA. | Não | Padrão `false`; imprime requisições e respostas detalhadas. |
    | `SKIP_AI_ANALYSIS` | Pular análise de IA e enviar notificações direto. | Não | Padrão `false`. |
    | `ENABLE_THINKING` | Ativar o parâmetro `enable_thinking`. | Não | Padrão `false`. Alguns modelos não aceitam esse parâmetro. |
    | `SERVER_PORT` | Porta do serviço Web UI. | Não | Padrão `8000`. |
    | `WEB_USERNAME` | Usuário de login do painel Web. | Não | Padrão `admin`. Troque em produção. |
    | `WEB_PASSWORD` | Senha do painel Web. | Não | Padrão `admin123`. Use senha forte em produção. |

    > 💡 **Dica de depuração**: se receber erro 404 ao configurar a API de IA, teste primeiro com provedores da Aliyun ou Volcano para garantir que o fluxo básico funciona antes de tentar outros. Alguns provedores exigem configuração especial.

    > 🔐 **Segurança**: a interface Web usa autenticação básica. O padrão é `admin` / `admin123`; altere em produção!

2. **Obter estado de login (importante!)**: para que o crawler acesse o Goofish logado, é preciso fornecer credenciais válidas. Use preferencialmente o Web UI:

    **Via Web UI (recomendado)**
    1. Pule este passo por enquanto e vá direto ao Passo 3 para iniciar o serviço Web.
    2. No Web UI, abra **"Configurações do Sistema"**.
    3. Encontre "Arquivo de estado de login" e clique em **"Atualizar manualmente"**.
    4. Siga as instruções do modal:
       - No seu computador, instale a [extensão de extração de login do Goofish](https://chromewebstore.google.com/detail/xianyu-login-state-extrac/eidlpfjiodpigmfcahkmlenhppfklcoa) no Chrome
       - Abra e faça login no site do Goofish
       - Clique no ícone da extensão na barra do navegador
       - Clique em "Extrair estado de login"
       - Clique em "Copiar para a área de transferência"
       - Cole o conteúdo no Web UI e salve

    Esse método dispensa interface gráfica no servidor e é o mais simples.

    **Alternativa: rodar o script de login**
    Se puder rodar com interface gráfica localmente ou em um servidor com desktop, use:

    ```bash
    python login.py
    ```

    Um navegador será aberto; use o app do Goofish no celular para escanear o QR Code. Após o login, a janela fecha e o arquivo `xianyu_state.json` é criado no diretório raiz.

### Passo 3: Iniciar o serviço Web

Tudo pronto? Suba o servidor de administração:

```bash
python web_server.py
```

### Passo 4: Começar a usar

Abra `http://127.0.0.1:8000` no navegador.

1. Na página **“Gerenciamento de Tarefas”**, clique em **“Criar nova tarefa”**.
2. No modal, descreva em linguagem natural o que você quer (ex.: “Quero uma câmera Sony A7M4 com 95% de novo, até 13k, menos de 5000 cliques”) e preencha nome/keyword.
3. Clique em criar; a IA gera os critérios complexos para você.
4. De volta à tela principal, adicione agendamento ou clique em iniciar para monitorar automaticamente!

## 🐳 Deploy com Docker (recomendado)

Use Docker para empacotar o app com dependências e ter deploy rápido e consistente.

### Passo 1: Preparar o ambiente (igual ao local)

1. **Instale o Docker**: veja [Docker Engine](https://docs.docker.com/engine/install/).

2. **Clone e configure**:

    ```bash
    git clone https://github.com/opastorello/ai-goofish-monitor
    cd ai-goofish-monitor
    ```

3. **Crie o `.env`**: siga as instruções do **[Guia Rápido](#-guia-rápido-recomendado-usar-o-web-ui)** para preencher o `.env` na raiz.

4. **Obter o estado de login (crítico!)**: não dá para fazer login via QR Code dentro do container. Após subir, configure pelo Web UI:
    1. No host, rode `docker-compose up -d`.
    2. Abra `http://127.0.0.1:8000` no navegador.
    3. Vá para **Configurações do Sistema** e suba o arquivo `xianyu_state.json` ou cole os dados extraídos pela extensão.

### Passo 2: Subir o serviço com Docker Compose

Com `.env` pronto, execute:

```bash
docker-compose up -d
```

O `docker-compose.yaml` já cria um volume para `xianyu_state.json`:

```yaml
services:
  ai-goofish-monitor:
    volumes:
      - ./xianyu_state.json:/app/xianyu_state.json
```

Após subir, acesse `http://127.0.0.1:8000` para usar o painel.

### Passo 3: Atualizar ou parar os serviços

- **Recriar após mudança**: `docker-compose up -d --build`
- **Parar**: `docker-compose down`
- **Ver logs**: `docker-compose logs -f`

## 🧩 Estrutura do Projeto

```
ai-goofish-monitor
├── prompts/                 # Modelos de prompt para análise de IA
├── static/                  # Arquivos estáticos do front-end (CSS/JS/Imagens)
├── templates/               # Templates HTML para o Web UI
├── config.json.example      # Exemplo de configuração de tarefas
├── web_server.py            # Servidor do painel Web
├── spider_v2.py             # Crawler principal com análise de IA
├── login.py                 # Script de login via QR Code
└── ...
```

## ⚙️ Configuração de Tarefas

O arquivo `config.json` define tarefas e parâmetros globais. Exemplo:

```json
{
  "global_settings": {
    "scheduler_interval_minutes": 5,
    "max_concurrent_tasks": 3
  },
  "tasks": [
    {
      "task_name": "Carrinho de bebê",
      "keyword": "babycare carrinho",
      "enable_ai_analysis": true,
      "ai_prompt_file": "prompts/babycare_criteria.txt",
      "filters": {
        "price_range": [300, 2000],
        "max_days_since_posted": 3,
        "min_seller_ratings": 95
      }
    }
  ]
}
```

### Campos principais das tarefas

- **`task_name`**: Nome da tarefa (exibido no painel e nas notificações).
- **`keyword`**: Palavra-chave de busca no Goofish.
- **`enable_ai_analysis`**: Ativa a análise multimodal da IA.
- **`ai_prompt_file`**: Caminho para o arquivo `.txt` com seus critérios de análise.
- **`filters`**: Filtros adicionais (faixa de preço, tempo desde a publicação, etc.).

## 🤖 Como funciona a análise com IA

1. O crawler coleta dados do item (título, preço, localização, reputação do vendedor) e imagens.
2. As imagens são baixadas temporariamente e enviadas ao modelo de IA.
3. O prompt de critérios define as regras para recomendar ou não.
4. Se recomendado, o item é enviado via ntfy/WeChat/Bark e salvo no log de resultados.

## 📄 Logs e Resultados

- **`logs/`**: logs detalhados de execução e depuração.
- **`output/`**: registros dos itens analisados e recomendados.
- **Painel Web**: visualize logs em tempo real e resultados filtrados.

## 🔒 Segurança

- As credenciais ficam no `.env` (não faça commit!).
- O painel usa autenticação básica; altere usuário/senha padrão em produção.
- Se usar proxies, valide a origem para evitar vazamento de dados.

## ❓ Suporte e Contribuições

- Abra issues e PRs no GitHub para reportar problemas ou sugerir melhorias.
- PRs são bem-vindos! Descreva claramente a mudança e o motivo.

## 🧠 Licença

Distribuído sob licença MIT. Consulte `LICENSE` para detalhes.

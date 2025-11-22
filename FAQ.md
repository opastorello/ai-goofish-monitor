# Perguntas Frequentes (FAQ)

Este documento reúne problemas comuns e soluções ao usar o projeto AI-Goofish-Monitor.

### **Q1: Análise de IA e configuração**

#### Pergunta: Por que o log mostra `Tarefa não possui prompt de IA, pulando análise` ou `Recomendação da IA: pendente; Motivo: sem análise`?
**Resposta:** Porque a análise de IA não está habilitada ou configurada corretamente para essa tarefa.
1. Abra o arquivo `config.json`.
2. Encontre a tarefa desejada.
3. Certifique-se de que `enable_ai_analysis` está como `true`.
4. Aponte `ai_prompt_file` para um arquivo `.txt` existente com seus critérios. Se ainda não tem um, use `prompts/macbook_criteria.txt` como modelo.

#### Pergunta: Ao criar ou executar uma tarefa recebo "Request timed out", "Connection error", "erro 404" ou `função get_ai_analysis ... tentativa falhou`. O que significa?
**Resposta:** Normalmente é rede ou configuração da IA indicando que o servidor não consegue alcançar o `OPENAI_BASE_URL` definido no `.env`. Verifique:
- **Chave de API:** Confirme que `OPENAI_API_KEY` está correta e ativa, e que há saldo suficiente.
- **Rede:** Garanta que o servidor consegue acessar o endereço em `OPENAI_BASE_URL`. Na China continental, acessar serviços externos (OpenAI, Gemini) pode exigir proxy. Agora você pode configurar `PROXY_URL` no `.env` para resolver.
- **Endpoint errado:** Confirme que o `OPENAI_BASE_URL` está correto e o serviço está online. Para erros 404, teste primeiro APIs de provedores locais como Aliyun ou Volcano.
- **Nome do modelo:** Confira se `OPENAI_MODEL_NAME` corresponde a um modelo válido do provedor escolhido.

#### Pergunta: E se o modelo de IA escolhido não suportar análise de imagens?
**Resposta:** A análise multimodal é essencial neste projeto, então **é obrigatório** escolher um modelo com suporte a imagens. Se o modelo não aceitar imagens, a análise falhará ou ficará ruim. No `.env`, troque `OPENAI_MODEL_NAME` por um modelo com visão, como `gpt-4o`, `gemini-1.5-pro`, `deepseek-v2`, `qwen-vl-plus` etc.

#### Pergunta: Como configurar Gemini / Qwen ou outro modelo que não seja do OpenAI?
**Resposta:** Em teoria, qualquer modelo com API compatível com OpenAI funciona. Foque em configurar estes três campos no `.env`:
- `OPENAI_API_KEY`: sua chave do provedor.
- `OPENAI_BASE_URL`: endpoint compatível. Veja a documentação do provedor; normalmente `https://api.seu-provedor.com/v1` (sem `/chat/completions` no final).
- `OPENAI_MODEL_NAME`: nome exato do modelo, com suporte a imagens, por exemplo `gemini-2.5-flash`.
- **Exemplo:** Se a documentação disser que o endpoint de Completions é `https://xx.xx.com/v1/chat/completions`, então `OPENAI_BASE_URL` deve ser `https://xx.xx.com/v1`.

#### Pergunta: Por que o teste de conexão com o modelo falha com "Invalid JSON payload received. Unknown name \"enable_thinking\": Cannot find field"?
**Resposta:** Alguns modelos não aceitam o parâmetro `enable_thinking`. O projeto permite controlar isso pela variável `ENABLE_THINKING`:
- **Solução:** defina `ENABLE_THINKING=false` no `.env` e rode o teste novamente.
- **Padrão:** a partir da versão v1.0, `ENABLE_THINKING` é `false` por padrão para compatibilizar com mais modelos.
- **Necessidade especial:** se o modelo precisar do parâmetro, mude para `true`.

### **Q3: Login e anti-scraping**

#### Pergunta: Por que o arquivo `xianyu_state.json` some sozinho?
**Resposta:** Quando o programa detecta que as credenciais no `xianyu_state.json` expiraram, ele apaga o arquivo para forçar você a fazer login novamente. Refaça o login e extraia o cookie com a extensão do Chrome.

#### Pergunta: Após algum tempo o Goofish detecta tráfego anormal ou exige captcha/arraste?
**Resposta:** É o mecanismo anti-scraping do site. Para reduzir o risco:
- **Desative o modo headless:** no `.env`, defina `RUN_HEADLESS=false`. Assim o navegador abre com interface e você pode completar o captcha manualmente; o programa segue depois.
- **Diminua a frequência:** em `config.json`, aumente `scheduler_interval_minutes` (por exemplo, de 5 para 15 ou 30 minutos).
- **Use proxy:** (avançado) configure `PROXY_URL` no `.env` para evitar bloqueio de IP.
- **Refaça login:** delete `xianyu_state.json` antigo e extraia novamente o cookie.

### **Q4: Ambiente e Deploy**

#### Pergunta: Rodar `login.py` ou `spider_v2.py` mostra erro de encoding relacionado a `'gbk' codec can't encode character`?
**Resposta:** Clássico problema de encoding no Windows. O projeto usa UTF-8.
- **Solução:** antes de rodar os scripts em PowerShell ou CMD, force UTF-8 com:

```powershell
setx PYTHONIOENCODING UTF-8
$env:PYTHONIOENCODING="UTF-8"
```

ou use `chcp 65001` para mudar a code page para UTF-8.

#### Pergunta: `login.py` pede `playwright install` ou exibe `Old Headless mode has been removed from the Chrome binary`.
**Resposta:** Faltam os binários de navegador do Playwright ou há incompatibilidade de versão. Certifique-se de instalar as dependências via `requirements.txt` e, se necessário, rode:

```bash
playwright install chromium
```

Se persistir, tente instalar/atualizar o Chromium manualmente.

#### Pergunta: Por que pyzbar falha para instalar no Windows?
**Resposta:** pyzbar precisa da biblioteca dinâmica zbar no Windows.
- **Solução (Windows):**
  - **Método 1 (recomendado):** instale via Chocolatey:
  ```powershell
  choco install zbar
  ```
  - **Método 2:** baixe `libzbar-64.dll` dos [releases do zbar](https://github.com/NaturalHistoryMuseum/pyzbar/releases) e coloque no diretório do Python ou no PATH.
  - **Método 3:** use conda:
  ```bash
  conda install -c conda-forge pyzbar
  ```
- **Usuários Linux:** instale o pacote do sistema:

```bash
sudo apt-get install libzbar0
```

#### Pergunta: Ao rodar `login.py` recebo `ModuleNotFoundError: No module named 'PIL'`. Por quê?
**Resposta:** Geralmente porque o Python é antigo ou as dependências não foram instaladas completamente. Recomendamos Python 3.10+.
- **Solução:**
  - Use Python 3.10 ou superior
  - Reinstale as dependências:

```bash
pip install -r requirements.txt
```

  - Se ainda falhar, instale Pillow separadamente:

```bash
pip install Pillow
```

#### Pergunta: Usando Docker aparece log `Erro ao inicializar o cliente`.
**Resposta:** Geralmente falta memória compartilhada no container. Ao rodar `docker run`, adicione `--shm-size=1gb`, por exemplo:

```bash
docker run --shm-size=1gb ...
```

Se usar `docker-compose`, adicione `shm_size: '1gb'` no serviço no `docker-compose.yaml`.

#### Pergunta: Posso fazer deploy no NAS Synology via Docker?
**Resposta:** Sim. O procedimento é igual ao deploy padrão com Docker. Em alguns casos, pode ser necessário configurar permissões de repositório de imagens no Synology para puxar as imagens corretamente.

### **Q5: Uso das funcionalidades**

#### Pergunta: Como defino a frequência das tarefas agendadas?
**Resposta:** O intervalo é controlado pelo parâmetro global `scheduler_interval_minutes` em `config.json`. Ele define de quantos em quantos minutos o agendador verifica e executa as tarefas habilitadas. Por exemplo, `10` significa que todas as tarefas ativas rodarão a cada 10 minutos.

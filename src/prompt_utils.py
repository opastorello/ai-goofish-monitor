import asyncio
import json
import os
import sys

import aiofiles

from src.config import MODEL_NAME, client

# The meta-prompt to instruct the AI
META_PROMPT_TEMPLATE = """
Você é um mestre mundial de engenharia de prompts de IA. Sua tarefa é, com base no **requisito de compra** fornecido pelo usuário e imitando um **exemplo de referência**, gerar um novo texto de **critérios de análise** para o módulo de análise do robô de monitoramento do Xianyu (codinome EagleEye).

Sua resposta deve seguir rigorosamente a estrutura, o tom e os princípios centrais do **exemplo de referência**, mas o conteúdo precisa ser totalmente adaptado ao **requisito de compra** do usuário. O texto final servirá como guia de raciocínio para a análise da IA.

---
Este é o **exemplo de referência** (`macbook_criteria.txt`):
```text
{reference_text}
```
---

Este é o **requisito de compra** do usuário:
```text
{user_description}
```
---

Agora gere o novo texto de **critérios de análise**. Atenção:
1. **Somente** retorne o novo conteúdo gerado, sem explicações extras, títulos ou blocos de código.
2. Mantenha marcadores de versão como `[V6.3 Core Upgrade]` e `[V6.4 Logic Fix]` para preservar o formato.
3. Substitua tudo o que estiver relacionado a "MacBook" por informações relevantes ao produto desejado pelo usuário.
4. Reflita e produza "Princípios de Reprovação Imediata" e uma "Lista de Sinais de Alerta" para o novo tipo de produto.
"""


async def generate_criteria(user_description: str, reference_file_path: str) -> str:
    """
    Generates a new criteria file content using AI.
    """
    if not client:
        raise RuntimeError("Cliente de IA não inicializado; não é possível gerar critérios. Verifique a configuração do .env.")

    print(f"Lendo arquivo de referência: {reference_file_path}")
    try:
        with open(reference_file_path, 'r', encoding='utf-8') as f:
            reference_text = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Arquivo de referência não encontrado: {reference_file_path}")
    except IOError as e:
        raise IOError(f"Falha ao ler arquivo de referência: {e}")

    print("Montando instrução para envio à IA...")
    prompt = META_PROMPT_TEMPLATE.format(
        reference_text=reference_text,
        user_description=user_description
    )

    print("Chamando a IA para gerar novos critérios. Aguarde...")
    try:
        from src.config import get_ai_request_params
        
        response = await client.chat.completions.create(
            **get_ai_request_params(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5 # Lower temperature for more predictable structure
            )
        )
        generated_text = response.choices[0].message.content
        print("A IA gerou o conteúdo com sucesso.")

        # Lida com a possibilidade de content ser None
        if generated_text is None:
            raise RuntimeError("A resposta da IA está vazia; verifique a configuração do modelo ou tente novamente.")
        
        return generated_text.strip()
    except Exception as e:
        print(f"Erro ao chamar a API da OpenAI: {e}")
        raise e


async def update_config_with_new_task(new_task: dict, config_file: str = "config.json"):
    """
    Adiciona uma nova tarefa ao arquivo de configuração JSON indicado.
    """
    print(f"Atualizando arquivo de configuração: {config_file}")
    try:
        # Lê a configuração existente
        config_data = []
        if os.path.exists(config_file):
            async with aiofiles.open(config_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                # Trata arquivo vazio
                if content.strip():
                    config_data = json.loads(content)

        # Acrescenta nova tarefa
        config_data.append(new_task)

        # Grava novamente no arquivo
        async with aiofiles.open(config_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(config_data, ensure_ascii=False, indent=2))

        print(f"Sucesso! Nova tarefa '{new_task.get('task_name')}' adicionada a {config_file} e habilitada.")
        return True
    except json.JSONDecodeError:
        sys.stderr.write(f"Erro: o arquivo de configuração {config_file} está em formato inválido.\n")
        return False
    except IOError as e:
        sys.stderr.write(f"Erro: falha ao ler/gravar o arquivo de configuração: {e}\n")
        return False

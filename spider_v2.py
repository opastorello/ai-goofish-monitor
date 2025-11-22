import asyncio
import sys
import os
import argparse
import json

from src.config import STATE_FILE
from src.scraper import scrape_xianyu


async def main():
    parser = argparse.ArgumentParser(
        description="Monitor de produtos do Goofish com suporte a múltiplas tarefas e análise de IA em tempo real.",
        epilog="""
Exemplos de uso:
  # Executar todas as tarefas definidas em config.json
  python spider_v2.py

  # Executar apenas a tarefa chamada "Sony A7M4" (geralmente chamado pelo agendador)
  python spider_v2.py --task-name "Sony A7M4"

  # Modo de depuração: executar todas as tarefas, mas cada uma só processa os 3 primeiros novos produtos
  python spider_v2.py --debug-limit 3
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--debug-limit", type=int, default=0, help="Modo de depuração: cada tarefa processa apenas N novos produtos (0 significa sem limite)")
    parser.add_argument("--config", type=str, default="config.json", help="Caminho do arquivo de configuração das tarefas (padrão: config.json)")
    parser.add_argument("--task-name", type=str, help="Execute apenas a tarefa com o nome especificado (usado pelo agendador)")
    args = parser.parse_args()

    if not os.path.exists(STATE_FILE):
        sys.exit(f"Erro: o arquivo de estado de login '{STATE_FILE}' não existe. Execute login.py primeiro.")

    if not os.path.exists(args.config):
        sys.exit(f"Erro: o arquivo de configuração '{args.config}' não existe.")

    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            tasks_config = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        sys.exit(f"Erro: falha ao ler ou analisar o arquivo de configuração '{args.config}': {e}")

    # Ler o conteúdo de todos os arquivos de prompt
    for task in tasks_config:
        if task.get("enabled", False) and task.get("ai_prompt_base_file") and task.get("ai_prompt_criteria_file"):
            try:
                with open(task["ai_prompt_base_file"], 'r', encoding='utf-8') as f_base:
                    base_prompt = f_base.read()
                with open(task["ai_prompt_criteria_file"], 'r', encoding='utf-8') as f_criteria:
                    criteria_text = f_criteria.read()
                
                # Combinar dinamicamente para formar o prompt final
                task['ai_prompt_text'] = base_prompt.replace("{{CRITERIA_SECTION}}", criteria_text)
                
                # Validar se o prompt gerado é válido
                if len(task['ai_prompt_text']) < 100:
                    print(f"Aviso: o prompt gerado para a tarefa '{task['task_name']}' é muito curto ({len(task['ai_prompt_text'])} caracteres) e pode estar incorreto.")
                elif "{{CRITERIA_SECTION}}" in task['ai_prompt_text']:
                    print(f"Aviso: o prompt da tarefa '{task['task_name']}' ainda contém o marcador de posição; a substituição pode ter falhado.")
                else:
                    print(f"✅ Prompt da tarefa '{task['task_name']}' gerado com sucesso, comprimento: {len(task['ai_prompt_text'])} caracteres")

            except FileNotFoundError as e:
                print(f"Aviso: o arquivo de prompt da tarefa '{task['task_name']}' está ausente: {e}; a análise de IA dessa tarefa será ignorada.")
                task['ai_prompt_text'] = ""
            except Exception as e:
                print(f"Erro: a tarefa '{task['task_name']}' encontrou uma exceção ao processar o arquivo de prompt: {e}; a análise de IA dessa tarefa será ignorada.")
                task['ai_prompt_text'] = ""
        elif task.get("enabled", False) and task.get("ai_prompt_file"):
            try:
                with open(task["ai_prompt_file"], 'r', encoding='utf-8') as f:
                    task['ai_prompt_text'] = f.read()
                print(f"✅ Arquivo de prompt da tarefa '{task['task_name']}' lido com sucesso, comprimento: {len(task['ai_prompt_text'])} caracteres")
            except FileNotFoundError:
                print(f"Aviso: o arquivo de prompt '{task['ai_prompt_file']}' da tarefa '{task['task_name']}' não foi encontrado; a análise de IA dessa tarefa será ignorada.")
                task['ai_prompt_text'] = ""
            except Exception as e:
                print(f"Erro: a tarefa '{task['task_name']}' encontrou uma exceção ao ler o arquivo de prompt: {e}; a análise de IA dessa tarefa será ignorada.")
                task['ai_prompt_text'] = ""

    print("\n--- Iniciando a execução das tarefas de monitoramento ---")
    if args.debug_limit > 0:
        print(f"** Modo de depuração ativo: cada tarefa processará no máximo {args.debug_limit} novos produtos **")

    if args.task_name:
        print(f"** Modo de tarefa agendada: executando apenas a tarefa '{args.task_name}' **")

    print("--------------------")

    active_task_configs = []
    if args.task_name:
        # Se um nome de tarefa for especificado, localize apenas essa tarefa
        task_found = next((task for task in tasks_config if task.get('task_name') == args.task_name), None)
        if task_found:
            if task_found.get("enabled", False):
                active_task_configs.append(task_found)
            else:
                print(f"A tarefa '{args.task_name}' está desativada; ignorando a execução.")
        else:
            print(f"Erro: nenhuma tarefa chamada '{args.task_name}' foi encontrada no arquivo de configuração.")
            return
    else:
        # Caso contrário, carregue todas as tarefas ativadas conforme planejado
        active_task_configs = [task for task in tasks_config if task.get("enabled", False)]

    if not active_task_configs:
        print("Não há tarefas para executar; o programa será encerrado.")
        return

    # Criar uma co-rotina assíncrona para cada tarefa ativada
    coroutines = []
    for task_conf in active_task_configs:
        print(f"-> A tarefa '{task_conf['task_name']}' foi adicionada à fila de execução.")
        coroutines.append(scrape_xianyu(task_config=task_conf, debug_limit=args.debug_limit))

    # Executar todas as tarefas de forma concorrente
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    print("\n--- Todas as tarefas foram concluídas ---")
    for i, result in enumerate(results):
        task_name = active_task_configs[i]['task_name']
        if isinstance(result, Exception):
            print(f"A tarefa '{task_name}' foi interrompida devido a uma exceção: {result}")
        else:
            print(f"A tarefa '{task_name}' terminou normalmente; {result} novos produtos foram processados nesta execução.")

if __name__ == "__main__":
    asyncio.run(main())

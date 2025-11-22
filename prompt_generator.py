import os
import sys
import argparse
import asyncio

from src.prompt_utils import generate_criteria, update_config_with_new_task


async def main():
    parser = argparse.ArgumentParser(
        description=(
            "Use a IA para gerar um arquivo de critérios do monitor do Goofish "
            "com base em uma descrição de compra e um exemplo de referência, "
            "atualizando automaticamente o config.json."
        ),
        epilog="""
Exemplo de uso:
  python prompt_generator.py \\
    --description "Quero comprar uma câmera Sony A7M4 com pelo menos 95% de conservação, orçamento entre 10000 e 13000..." \\
    --output prompts/sony_a7m4_criteria.txt \\
    --task-name "Sony A7M4" \\
    --keyword "a7m4" \\
    --min-price "10000" \\
    --max-price "13000"
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--description", type=str, required=True, help="Descrição detalhada do que você deseja comprar.")
    parser.add_argument("--output", type=str, required=True, help="Caminho para salvar o novo arquivo de critérios gerado.")
    parser.add_argument("--reference", type=str, default="prompts/macbook_criteria.txt", help="Arquivo de referência a ser usado como modelo.")
    # Novos argumentos para o config.json
    parser.add_argument("--task-name", type=str, required=True, help="Nome da nova tarefa (ex.: 'Sony A7M4').")
    parser.add_argument("--keyword", type=str, required=True, help="Palavra-chave de busca da nova tarefa (ex.: 'a7m4').")
    parser.add_argument("--min-price", type=str, help="Preço mínimo desejado.")
    parser.add_argument("--max-price", type=str, help="Preço máximo permitido.")
    parser.add_argument("--max-pages", type=int, default=3, help="Número máximo de páginas a varrer (padrão: 3).")
    parser.add_argument('--no-personal-only', dest='personal_only', action='store_false', help="Se definido, não filtra apenas vendedores pessoais.")
    parser.set_defaults(personal_only=True)
    parser.add_argument("--config-file", type=str, default="config.json", help="Caminho do arquivo de configuração (padrão: config.json).")
    args = parser.parse_args()

    # Garante que o diretório de saída exista
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        generated_criteria = await generate_criteria(args.description, args.reference)
    except Exception as e:
        sys.exit(f"Erro: falha ao gerar os critérios de análise: {e}")


    if generated_criteria:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(generated_criteria)
            print(f"\nSucesso! Os novos critérios foram salvos em: {args.output}")
        except IOError as e:
            sys.exit(f"Erro: falha ao gravar o arquivo de saída: {e}")

        # Criar nova entrada de tarefa
        new_task = {
            "task_name": args.task_name,
            "enabled": True,
            "keyword": args.keyword,
            "max_pages": args.max_pages,
            "personal_only": args.personal_only,
            "ai_prompt_base_file": "prompts/base_prompt.txt",
            "ai_prompt_criteria_file": args.output
        }
        if args.min_price:
            new_task["min_price"] = args.min_price
        if args.max_price:
            new_task["max_price"] = args.max_price

        # Atualizar o config.json usando a função refatorada
        success = await update_config_with_new_task(new_task, args.config_file)
        if success:
            print("Agora você pode executar `python spider_v2.py` para iniciar todos os monitoramentos, incluindo a nova tarefa.")

if __name__ == "__main__":
    asyncio.run(main())

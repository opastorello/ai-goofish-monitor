# Guia de Testes

Este projeto utiliza o pytest como framework de testes. Abaixo estão as instruções para executá-los.

## Instalar dependências

Antes de rodar os testes, certifique-se de instalar todas as dependências de desenvolvimento:

```bash
pip install -r requirements.txt
```

## Executar os testes

### Executar todos os testes

```bash
pytest
```

### Executar um arquivo de teste específico

```bash
pytest tests/test_utils.py
```

### Executar uma função de teste específica

```bash
pytest tests/test_utils.py::test_safe_get
```

### Gerar relatório de cobertura

```bash
coverage run -m pytest
coverage report
coverage html  # gera o relatório HTML
```

## Estrutura dos arquivos de teste

```
tests/
├── __init__.py
├── conftest.py          # Configuração e fixtures compartilhadas dos testes
├── test_ai_handler.py   # Testes do módulo ai_handler.py
├── test_config.py       # Testes do módulo config.py
├── test_login.py        # Testes do script login.py
├── test_prompt_generator.py  # Testes do script prompt_generator.py
├── test_prompt_utils.py # Testes do módulo prompt_utils.py
├── test_scraper.py      # Testes do módulo scraper.py
├── test_spider_v2.py    # Testes do script spider_v2.py
└── test_utils.py        # Testes do módulo utils.py
```

## Escrevendo novos testes

1. Crie um novo arquivo em `tests/` com nome iniciando em `test_`
2. Nomeie funções de teste com o prefixo `test_`
3. Para funções assíncronas, use o decorador `@pytest.mark.asyncio`
4. Use o módulo `unittest.mock` para simular dependências externas e efeitos colaterais

## Observações

1. Alguns testes podem exigir mocks complexos, especialmente os que envolvem Playwright
2. Alguns testes podem precisar de conexão real com a internet ou serviços externos
3. Sempre que possível, utilize dados simulados em vez de dados reais
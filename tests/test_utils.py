import pytest
import json
import os
from unittest.mock import patch, mock_open
from src.utils import (
    safe_get,
    get_link_unique_key,
    format_registration_days,
    random_sleep,
    save_to_jsonl,
    convert_goofish_link,
    retry_on_failure
)


def test_safe_get():
    """Testa a função safe_get com diferentes entradas."""
    test_data = {
        "level1": {
            "level2": {
                "value": "found"
            }
        }
    }
    
    # Test successful retrieval
    assert safe_get(test_data, 'level1', 'level2', 'value') == "found"
    
    # Test default value when key not found
    assert safe_get(test_data, 'level1', 'missing', default="default") == "default"
    
    # Test None when no default specified and key not found
    assert safe_get(test_data, 'level1', 'missing') is None


def test_get_link_unique_key():
    """Testa a função get_link_unique_key."""
    # Test with valid URL
    url = "https://item.goofish.com/item.htm?id=12345&other=param"
    assert get_link_unique_key(url) == "12345"
    
    # Test with URL without id parameter
    url = "https://item.goofish.com/item.htm?other=param"
    assert get_link_unique_key(url) == url


def test_format_registration_days():
    """Testa a função format_registration_days."""
    # Testes com quantidades válidas de dias
    assert format_registration_days(365) == "Na Xianyu há 1 ano(s)"
    assert format_registration_days(30) == "Na Xianyu há 1 mês(es)"
    assert format_registration_days(1) == "Na Xianyu há menos de um mês"
    assert format_registration_days(0) == "Desconhecido"
    assert format_registration_days(400) == "Na Xianyu há 1 ano(s) e 1 mês(es)"


def test_convert_goofish_link():
    """Testa a função convert_goofish_link."""
    # Teste com link de desktop
    pc_link = "https://item.goofish.com/item.htm?id=12345"
    mobile_link = "https://m.goofish.com/item.htm?id=12345"
    assert convert_goofish_link(pc_link) == mobile_link

    # Teste com link que já é mobile
    assert convert_goofish_link(mobile_link) == mobile_link

    # Teste com link que não é do Goofish
    other_link = "https://other.com/item.htm?id=12345"
    assert convert_goofish_link(other_link) == other_link


@patch("src.utils.asyncio.sleep")
async def test_random_sleep(mock_sleep):
    """Testa a função random_sleep."""
    # Usa mock para evitar atraso real
    mock_sleep.return_value = None

    # Verifica se a função chama sleep
    await random_sleep(0.001, 0.002)
    assert mock_sleep.called


@patch("builtins.open", new_callable=mock_open)
@patch("src.utils.os.makedirs")
def test_save_to_jsonl(mock_makedirs, mock_file):
    """Testa a função save_to_jsonl."""
    # Dados de teste
    test_data = {"key": "value"}
    keyword = "test_keyword"

    # Chama a função
    save_to_jsonl(test_data, keyword)

    # Verifica se o diretório foi criado
    mock_makedirs.assert_called_once_with("jsonl", exist_ok=True)

    # Verifica se o arquivo foi gravado
    mock_file.assert_called_once_with(os.path.join("jsonl", "test_keyword_full_data.jsonl"), "a", encoding="utf-8")


def test_retry_on_failure():
    """Testa o decorador retry_on_failure."""
    attempts = 0
    
    @retry_on_failure(retries=2, delay=0.001)
    def failing_function():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise Exception("Intentional failure")
        return "success"
    
    # Deve funcionar na segunda tentativa
    result = failing_function()
    assert result == "success"
    assert attempts == 2

    # Reinicia para o próximo teste
    attempts = 0
    
    @retry_on_failure(retries=1, delay=0.001)
    def always_failing_function():
        nonlocal attempts
        attempts += 1
        raise Exception("Always fails")
    
    # Deve falhar após as tentativas
    with pytest.raises(Exception, match="Always fails"):
        always_failing_function()
    assert attempts == 2
from src.ai_output_language import (
    DEFAULT_OUTPUT_LANGUAGE,
    apply_output_language,
    normalize_output_language,
)

PROMPT = "你是分析专家。\n输出 JSON。"


def test_default_language_leaves_prompt_untouched():
    assert apply_output_language(PROMPT, None) == PROMPT
    assert apply_output_language(PROMPT, "") == PROMPT
    assert apply_output_language(PROMPT, "zh-CN") == PROMPT


def test_portuguese_and_english_append_an_instruction():
    pt = apply_output_language(PROMPT, "pt-BR")
    assert pt.startswith(PROMPT.rstrip())
    assert "Brazilian Portuguese" in pt and "reason" in pt and "NEEDS_MANUAL_CHECK" in pt
    assert "English" in apply_output_language(PROMPT, "en-US")


def test_unknown_language_falls_back_to_default():
    assert normalize_output_language("fr-FR") == DEFAULT_OUTPUT_LANGUAGE
    assert apply_output_language(PROMPT, "fr-FR") == PROMPT


def test_empty_prompt_stays_empty():
    assert apply_output_language("", "pt-BR") == ""

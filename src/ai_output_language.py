"""Output language for the free-text fields written by the AI analysis."""
from typing import Optional

DEFAULT_OUTPUT_LANGUAGE = "zh-CN"
_LANGUAGE_NAMES = {
    "en-US": "English",
    "pt-BR": "Brazilian Portuguese (português do Brasil)",
}
SUPPORTED_OUTPUT_LANGUAGES = (DEFAULT_OUTPUT_LANGUAGE, *_LANGUAGE_NAMES)


def normalize_output_language(value: Optional[str]) -> str:
    """Return a supported language code; anything unknown falls back to the default."""
    text = (value or "").strip()
    return text if text in SUPPORTED_OUTPUT_LANGUAGES else DEFAULT_OUTPUT_LANGUAGE


def apply_output_language(prompt: str, language: Optional[str]) -> str:
    """
    Append an output-language instruction to the analysis prompt. The prompts are
    written in Chinese, so the default language leaves the prompt unchanged.
    """
    code = normalize_output_language(language)
    if not prompt or code == DEFAULT_OUTPUT_LANGUAGE:
        return prompt
    return (
        f"{prompt.rstrip()}\n\n"
        "### Output language\n"
        f"Write every free-text value of the JSON object (especially `reason` and any explanation "
        f"inside `criteria_analysis`) in {_LANGUAGE_NAMES[code]}. "
        "Keep every JSON key and every fixed value (booleans, enum values such as "
        "PASS / FAIL / NEEDS_MANUAL_CHECK, seller_type values, prompt_version) exactly as specified "
        "above, and do not output anything outside the JSON object.\n"
    )

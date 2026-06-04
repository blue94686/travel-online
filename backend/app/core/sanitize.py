"""Input sanitization and sensitive word filtering."""
import re

# Basic sensitive word list (extend as needed)
SENSITIVE_WORDS = {
    "色情", "赌博", "毒品", "枪支", "弹药", "诈骗", "假币",
    "暴力", "恐怖", "自杀", "传销", "法轮功",
}

# HTML tag pattern
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not text:
        return ""
    text = _TAG_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def escape_html(text: str) -> str:
    """Escape HTML entities for safe display."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def check_sensitive_words(text: str) -> str | None:
    """Return the first sensitive word found, or None."""
    if not text:
        return None
    for word in SENSITIVE_WORDS:
        if word in text:
            return word
    return None


def sanitize_comment(text: str, max_length: int = 2000) -> tuple[str, str | None]:
    """Sanitize user comment. Returns (cleaned_text, error_message).

    error_message is None if the comment passes all checks.
    """
    if not text or not text.strip():
        return "", "评论内容不能为空"

    cleaned = sanitize_html(text)
    if not cleaned:
        return "", "评论内容不能为空（过滤后为空）"

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    bad_word = check_sensitive_words(cleaned)
    if bad_word:
        return "", f"内容包含不当词汇"

    return cleaned, None

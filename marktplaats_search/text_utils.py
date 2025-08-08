"""
Text cleaning and sanitization utilities.
Provides consistent text processing across Python backend and can be mirrored in JavaScript frontend.
"""

import html
import re


def clean_text(text: str | None) -> str | None:
    """
    Clean and normalize text content.

    Removes extra whitespace, normalizes line breaks, and ensures consistent formatting.

    Args:
        text: Raw text input

    Returns:
        Cleaned text or None if input is empty

    Examples:
        >>> clean_text("  Hello   world  \\n  ")
        "Hello world"
        >>> clean_text("")
        None
    """
    if not text:
        return None

    # Strip leading/trailing whitespace and normalize internal whitespace
    cleaned = re.sub(r"\s+", " ", text.strip())

    # Return None for empty strings after cleaning
    return cleaned if cleaned else None


def sanitize_html(text: str | None) -> str | None:
    """
    Sanitize text for safe HTML output.

    Escapes HTML characters to prevent XSS attacks while preserving text content.

    Args:
        text: Text that may contain HTML characters

    Returns:
        HTML-escaped text safe for browser display

    Examples:
        >>> sanitize_html("<script>alert('xss')</script>")
        "&lt;script&gt;alert('xss')&lt;/script&gt;"
        >>> sanitize_html("Price: €500 & more")
        "Price: €500 &amp; more"
    """
    if not text:
        return text

    return html.escape(text)


def clean_description(text: str | None) -> str | None:
    """
    Clean and normalize description text, removing price and metadata pollution.

    Specifically designed for Marktplaats listing descriptions that often contain
    repeated price information and metadata that pollutes the actual description.

    Args:
        text: Raw description text from listing

    Returns:
        Cleaned description or None if too short/empty

    Examples:
        >>> clean_description("Great laptop €500 details €500")
        "Great laptop"
        >>> clean_description("€500 details")
        None  # Too short after cleaning
    """
    if not text:
        return None

    # Start with basic text cleaning
    cleaned = clean_text(text)
    if not cleaned:
        return None

    # Remove price patterns that commonly appear in descriptions
    cleaned = re.sub(r"€\s*[\d.,]+(?:\s*,\d+)?\s*", "", cleaned)  # Remove Euro prices
    cleaned = re.sub(r"\$\s*[\d.,]+\s*", "", cleaned)  # Remove Dollar prices
    cleaned = re.sub(r"[\d,]+\s*€\s*", "", cleaned)  # Remove reversed Euro format

    # Remove metadata patterns more aggressively
    cleaned = re.sub(r"\s*details\s*", "", cleaned, flags=re.I)  # Remove "details" text
    cleaned = re.sub(r"🇳🇱\s*", "", cleaned)  # Remove Netherlands flag emoji

    # Remove condition and shipping info - more comprehensive patterns
    cleaned = re.sub(
        r"\s*(Gebruikt|Nieuw|Zo goed als nieuw|Used|New|Like new)\s*", "", cleaned, flags=re.I
    )
    cleaned = re.sub(
        r"\s*(Ophalen|Verzenden|Ophalen of Verzenden|Pickup|Shipping)\s*",
        "",
        cleaned,
        flags=re.I,
    )

    # Remove title repetition - often the description starts with title + price
    # Split on common patterns and take meaningful content
    parts = re.split(r"€[\d.,]+(?:,\d+)?details", cleaned, maxsplit=1, flags=re.I)
    if len(parts) > 1:
        cleaned = parts[1].strip()

    # Remove standalone price mentions that remain
    cleaned = re.sub(r"€[\d.,]+(?:,\d+)?", "", cleaned)

    # Remove common trailing elements
    cleaned = re.sub(r"\s*(Alle|All)\s*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*\|\s*$", "", cleaned)  # Remove trailing pipe

    # Clean up punctuation
    cleaned = re.sub(r"!+", "!", cleaned)  # Multiple ! to single !
    cleaned = re.sub(r"\s*!\s*$", "", cleaned)  # Remove trailing !
    cleaned = re.sub(r",\s*$", "", cleaned)  # Remove trailing comma

    # Clean up whitespace again after all the removals
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Return None if cleaned text is too short or mostly punctuation
    if len(cleaned) < 10 or len(re.sub(r"[^a-zA-Z0-9\s]", "", cleaned)) < 5:
        return None

    return cleaned


def clean_title(text: str | None) -> str | None:
    """
    Clean and normalize title text.

    Removes price information and details text that commonly pollute titles
    from automated scraping.

    Args:
        text: Raw title text

    Returns:
        Cleaned title text

    Examples:
        >>> clean_title("iPhone 12 €500 details")
        "iPhone 12"
        >>> clean_title("Laptop | €800 | details")
        "Laptop"
    """
    if not text:
        return None

    # Start with basic cleaning
    cleaned = clean_text(text)
    if not cleaned:
        return None

    # Remove various price patterns that can appear anywhere in title
    cleaned = re.sub(r"€\s*[\d.,]+\s*,?\s*", "", cleaned)  # Remove Euro prices with optional comma
    cleaned = re.sub(r"\$\s*[\d.,]+\s*,?\s*", "", cleaned)  # Remove Dollar prices
    cleaned = re.sub(r"[\d,]+\s*€\s*,?\s*", "", cleaned)  # Remove reversed Euro format
    cleaned = re.sub(r"€\s*[\d.,]+[^a-zA-Z]*$", "", cleaned)  # Remove trailing Euro prices

    # Remove details text and common clutter
    cleaned = re.sub(r"\s*details\s*.*$", "", cleaned, flags=re.I)  # Remove details text
    cleaned = re.sub(
        r"^\s*[Nn]u ook ideal in \d*", "", cleaned
    )  # Remove "Nu ook ideal in X" prefix
    cleaned = re.sub(r"\s*\d+\s*$", "", cleaned)  # Remove trailing numbers
    cleaned = re.sub(r"\|\s*$", "", cleaned)  # Remove trailing pipe
    cleaned = re.sub(r",\s*$", "", cleaned)  # Remove trailing comma

    # Final whitespace normalization
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned if cleaned else None


def extract_location(text: str | None) -> str | None:
    """
    Extract location information from text.

    Looks for Dutch location patterns commonly found in Marktplaats listings.

    Args:
        text: Text containing potential location information

    Returns:
        Extracted location string or None
    """
    if not text:
        return None

    # Look for patterns like "op 5 km", "in Amsterdam", "te koop in", etc.
    location_patterns = [
        r"(?:op|in|te koop in|from)\s+([^,\n\r]+?)(?:\s+(?:\d+\s*km|$))",
        r"(\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:,|\.|$)",  # City names
    ]

    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            location = clean_text(match.group(1))
            if location and len(location) < 50:  # Reasonable location length
                return location

    return None


def validate_text_length(text: str | None, min_length: int = 1, max_length: int = 1000) -> bool:
    """
    Validate text length constraints.

    Args:
        text: Text to validate
        min_length: Minimum required length
        max_length: Maximum allowed length

    Returns:
        True if text meets length requirements
    """
    if not text:
        return min_length == 0

    return min_length <= len(text) <= max_length


def truncate_text(text: str | None, max_length: int, suffix: str = "...") -> str | None:
    """
    Truncate text to specified length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating

    Returns:
        Truncated text or original if within limits

    Examples:
        >>> truncate_text("This is a very long text", 10)
        "This is..."
    """
    if not text:
        return text

    if len(text) <= max_length:
        return text

    # Account for suffix length
    truncate_at = max_length - len(suffix)
    if truncate_at <= 0:
        return suffix[:max_length]

    return text[:truncate_at] + suffix

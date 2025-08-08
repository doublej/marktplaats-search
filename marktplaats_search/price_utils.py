"""
Price parsing and validation utilities.
Provides consistent price handling across the application to avoid data integrity issues.
"""

import re


def clean_and_parse_price(price_text: str) -> tuple[str, int | None]:
    """
    Clean and normalize price text, returning both display text and numeric value in cents.

    This function handles various Dutch price formats from Marktplaats:
    - "€ 500,00" -> ("€ 500,00", 50000)
    - "500" -> ("€ 500", 50000)
    - "vraagprijs" -> ("Price on request", None)
    - "gratis" -> ("€ 0", 0)

    Args:
        price_text: Raw price text from scraped content

    Returns:
        Tuple of (display_text, price_in_cents)

    Examples:
        >>> clean_and_parse_price("€ 500,00")
        ("€ 500,00", 50000)
        >>> clean_and_parse_price("vraagprijs")
        ("Price on request", None)
    """
    if not price_text:
        return "Price on request", None

    # Remove extra whitespace and normalize
    price = re.sub(r"\s+", " ", price_text.strip())

    # Handle various price formats
    if "vraagprijs" in price.lower() or "v.o.n" in price.lower():
        return "Price on request", None
    elif "gratis" in price.lower():
        return "€ 0", 0

    # Extract numeric value for sorting/filtering
    # Look for patterns like "500,00", "500.00", "1.500,00", "1,500.00"
    numeric_match = re.search(r"[\d.,]+", price)
    numeric_value = None

    if numeric_match:
        try:
            # Handle European number format (1.234,56) vs US format (1,234.56)
            number_str = numeric_match.group()

            # If there are both commas and dots, determine which is decimal separator
            if "," in number_str and "." in number_str:
                # European format: 1.234,56 (dot for thousands, comma for decimal)
                if number_str.rfind(",") > number_str.rfind("."):
                    number_str = number_str.replace(".", "").replace(",", ".")
                # US format: 1,234.56 (comma for thousands, dot for decimal)
                else:
                    number_str = number_str.replace(",", "")
            # Only comma (could be thousands separator or decimal)
            elif "," in number_str:
                # If comma is followed by exactly 2 digits, it's decimal separator
                if re.search(r",\d{2}$", number_str):
                    number_str = number_str.replace(",", ".")
                # Otherwise it's thousands separator
                else:
                    number_str = number_str.replace(",", "")

            # Convert to cents for precise integer storage
            numeric_value = int(float(number_str) * 100)

        except (ValueError, TypeError):
            numeric_value = None

    # Format display text
    if "€" not in price and numeric_value is not None:
        # Add euro sign if missing
        if numeric_value == 0:
            return "€ 0", numeric_value
        else:
            # Format with proper European style (comma as decimal separator)
            euros = numeric_value / 100
            if euros.is_integer():
                return f"€ {int(euros)}", numeric_value
            else:
                return f"€ {euros:.2f}".replace(".", ","), numeric_value

    return price, numeric_value


def euros_to_cents(euros: float) -> int:
    """Convert euros to cents for database storage."""
    return int(euros * 100)


def cents_to_euros(cents: int) -> float:
    """Convert cents to euros for display."""
    return cents / 100.0


def format_price_display(cents: int | None) -> str:
    """
    Format price in cents as display string.

    Args:
        cents: Price in cents, or None for unknown price

    Returns:
        Formatted price string

    Examples:
        >>> format_price_display(50000)
        "€ 500,00"
        >>> format_price_display(None)
        "Price on request"
    """
    if cents is None:
        return "Price on request"

    if cents == 0:
        return "€ 0"

    euros = cents / 100.0
    return f"€ {euros:.2f}".replace(".", ",")


def validate_price_range(price_from: int | None, price_to: int | None) -> bool:
    """
    Validate price range values.

    Args:
        price_from: Minimum price in euros
        price_to: Maximum price in euros

    Returns:
        True if valid price range, False otherwise
    """
    if price_from is not None and price_from < 0:
        return False

    if price_to is not None and price_to < 0:
        return False

    return not (price_from is not None and price_to is not None and price_from > price_to)


def normalize_price_for_search_params(price_euros: int | None) -> str | None:
    """
    Convert price in euros to cents string for Marktplaats search parameters.

    Args:
        price_euros: Price in euros

    Returns:
        Price in cents as string, or None

    Examples:
        >>> normalize_price_for_search_params(500)
        "50000"
    """
    if price_euros is None:
        return None
    return str(price_euros * 100)

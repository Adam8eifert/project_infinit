"""
Utility functions for normalizing and slugifying movement names.
Used for creating canonical identifiers without diacritics.
"""
import unicodedata
import re


def slugify(text: str) -> str:
    """
    Convert text to a slug suitable for canonical_name.
    
    - Removes diacritics (ě → e, ř → r, etc.)
    - Converts to lowercase
    - Replaces spaces and special chars with hyphens
    - Removes multiple consecutive hyphens
    
    Examples:
        "Hnutí Hare Kršna" → "hnuti-hare-krsna"
        "Baháʼí víra" → "bahai-vira"
        "Děti Boží" → "deti-bozi"
    
    Args:
        text: Input text with diacritics
    
    Returns:
        Slugified text without diacritics
    """
    if not text:
        return ""
    
    # Normalize unicode (NFD = decompose diacritics)
    text = unicodedata.normalize('NFD', text)
    
    # Remove combining characters (diacritics)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Strip leading/trailing hyphens
    text = text.strip('-')
    
    return text


def normalize_for_matching(text: str) -> str:
    """
    Normalize text for fuzzy matching (less aggressive than slugify).
    
    - Removes diacritics
    - Converts to lowercase
    - Preserves spaces
    
    Used for matching aliases to canonical names.
    
    Examples:
        "Hnutí Hare Kršna" → "hnuti hare krsna"
        "ISKCON" → "iskcon"
    
    Args:
        text: Input text
    
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Normalize unicode
    text = unicodedata.normalize('NFD', text)
    
    # Remove combining characters
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Convert to lowercase and strip
    text = text.lower().strip()
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text


if __name__ == "__main__":
    # Tests
    test_cases = [
        ("Hnutí Hare Kršna", "hnuti-hare-krsna"),
        ("Děti Boží", "deti-bozi"),
        ("Baháʼí víra", "bahai-vira"),
        ("Šinčchondži", "sincchondzi"),
        ("Ánanda Márga", "ananda-marga"),
        ("Církev sjednocení", "cirkev-sjednoceni"),
    ]
    
    print("Testing slugify():\n")
    for input_text, expected in test_cases:
        result = slugify(input_text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{input_text}' → '{result}' (expected: '{expected}')")

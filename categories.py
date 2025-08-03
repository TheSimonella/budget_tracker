import json
import os
from typing import Dict, Optional

# Default keyword-to-category mapping. This can be extended by users at runtime.
DEFAULT_CATEGORY_KEYWORDS: Dict[str, str] = {
    # Groceries
    'GROCERY': 'Groceries',
    'WALMART': 'Groceries',
    'KROGER': 'Groceries',
    'SAFEWAY': 'Groceries',
    'WHOLE FOODS': 'Groceries',
    'TRADER JOE': 'Groceries',
    'COSTCO': 'Groceries',
    'ALDI': 'Groceries',
    'TARGET': 'Groceries',
    'PUBLIX': 'Groceries',
    # Pharmacy / drug stores
    'CVS': 'Pharmacy',
    'WALGREENS': 'Pharmacy',
    'RITE AID': 'Pharmacy',
    # Coffee shops
    'STARBUCKS': 'Coffee',
    'DUNKIN': 'Coffee',
    # Fast food / dining
    'MCDONALD': 'Fast Food',
    'BURGER KING': 'Fast Food',
    'CHICK-FIL-A': 'Fast Food',
    'TACO BELL': 'Fast Food',
    'SUBWAY': 'Fast Food',
    'PIZZA HUT': 'Dining',
    'DOMINOS': 'Dining',
    'UBER EATS': 'Dining',
    'DOORDASH': 'Dining',
    'GRUBHUB': 'Dining',
    # Gas / transportation
    'EXXON': 'Gas',
    'SHELL': 'Gas',
    'CHEVRON': 'Gas',
    'BP': 'Gas',
    'SUNOCO': 'Gas',
    '7-ELEVEN': 'Gas',
    'UBER': 'Transportation',
    'LYFT': 'Transportation',
    # Housing / utilities
    'RENT': 'Rent/Mortgage',
    'MORTGAGE': 'Rent/Mortgage',
    'APARTMENTS': 'Rent/Mortgage',
    'LEASE': 'Rent/Mortgage',
    'UTILITIES': 'Utilities',
    'ELECTRIC': 'Utilities',
    'WATER': 'Utilities',
    'GAS CO': 'Utilities',
    'COMCAST': 'Internet',
    'XFINITY': 'Internet',
    'SPECTRUM': 'Internet',
    'VERIZON': 'Phone',
    'AT&T': 'Phone',
    'T-MOBILE': 'Phone',
    'SPRINT': 'Phone',
    # Entertainment / subscriptions
    'NETFLIX': 'Entertainment',
    'HULU': 'Entertainment',
    'SPOTIFY': 'Entertainment',
    'DISNEY+': 'Entertainment',
    'ADOBE': 'Subscriptions',
    'GITHUB': 'Subscriptions',
    'PATREON': 'Donations',
    # Shopping / tech
    'AMAZON': 'Shopping',
    'EBAY': 'Shopping',
    'APPLE': 'Shopping',
    'BEST BUY': 'Electronics',
    'IKEA': 'Home Improvement',
    'HOME DEPOT': 'Home Improvement',
    'LOWES': 'Home Improvement',
    'GAMESTOP': 'Entertainment',
    # Travel
    'DELTA': 'Travel',
    'UNITED': 'Travel',
    'AMERICAN AIRLINES': 'Travel',
    'SOUTHWEST': 'Travel',
    'MARRIOTT': 'Travel',
    'HILTON': 'Travel',
    'HOLIDAY INN': 'Travel',
    'AIRBNB': 'Travel',
    # Finance / payments
    'PAYPAL': 'Finance',
    'VENMO': 'Finance',
    'SQUARE': 'Finance',
    'INTUIT': 'Finance',
    # Insurance / health
    'INSURANCE': 'Insurance',
    'PROGRESSIVE': 'Insurance',
    'GEICO': 'Insurance',
    'STATE FARM': 'Insurance',
    'ALLSTATE': 'Insurance',
    'HOSPITAL': 'Healthcare',
    'MEDICAL': 'Healthcare',
    'DENTAL': 'Healthcare',
    'PHARMACY': 'Pharmacy',
    # Miscellaneous
    'CHARITY': 'Donations',
    'TAX': 'Taxes',
    'IRS': 'Taxes',
    'GOVERNMENT': 'Government',
    'COLLEGE': 'Education',
    'UNIVERSITY': 'Education',
    'BOOKS': 'Education',
}

# Location of the persistent keyword mapping file. Users can edit this file or
# add new keywords at runtime via ``add_keyword_category``.
_KEYWORDS_PATH = os.path.join(os.path.dirname(__file__), 'category_keywords.json')

try:
    with open(_KEYWORDS_PATH, 'r', encoding='utf-8') as fh:
        CATEGORY_KEYWORDS: Dict[str, str] = json.load(fh)
except FileNotFoundError:
    CATEGORY_KEYWORDS = DEFAULT_CATEGORY_KEYWORDS.copy()


def _save_keywords() -> None:
    """Persist ``CATEGORY_KEYWORDS`` to disk."""
    with open(_KEYWORDS_PATH, 'w', encoding='utf-8') as fh:
        json.dump(CATEGORY_KEYWORDS, fh, indent=2, sort_keys=True)


def categorize_merchant(merchant: str) -> Optional[str]:
    """Return the category for a merchant based on keyword matching."""
    upper = merchant.upper()
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in upper:
            return category
    return None


def add_keyword_category(keyword: str, category: str) -> None:
    """Add a new keyword mapping and persist it."""
    CATEGORY_KEYWORDS[keyword.upper()] = category
    _save_keywords()

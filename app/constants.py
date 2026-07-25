"""
Shared constants used across multiple features.

This file must NOT import anything from other app modules (models, routes,
etc.) — it exists specifically so that listings/routes.py and
admin/routes.py can both use the same CATEGORIES list without creating a
circular import between them.
"""

# Single source of truth for valid service categories. Used by:
#   - app/listings/routes.py  (to build the category tabs)
#   - app/admin/routes.py     (to build the category dropdown + validate it)
CATEGORIES = ["Home", "Office", "Deep Clean", "Move Out", "Eco", "Special"]

# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)


def objects_to_dict(objects: list, key_field: str) -> dict:
    """
    Converts a list of objects (dicts or objects with attributes) into a dictionary
    keyed by the value of `key_field` for each object.

    Args:
        objects (list): List of dicts or objects.
        key_field (str): The field name or key to use for dictionary keys.

    Returns:
        dict: Dictionary mapping key_field values to objects.
    """
    return {
        obj[key_field] if isinstance(obj, dict) else getattr(obj, key_field, None): obj
        for obj in objects
        if (obj[key_field] if isinstance(obj, dict) else getattr(obj, key_field, None))
        is not None
    }

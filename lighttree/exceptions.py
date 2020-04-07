class NotFoundNodeError(Exception):
    """Requested node identifier is not present in tree"""

    pass


class MultipleRootError(Exception):
    """Tree root is already declared."""

    pass


class DuplicatedNodeError(Exception):
    """Node identifier already exists in tree."""

    pass

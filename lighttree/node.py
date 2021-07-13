#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
from typing import Optional, Any, Tuple, Union


class Node(object):
    def __init__(
        self,
        identifier: Optional[str] = None,
        auto_uuid: bool = True,
        keyed: bool = True,
        accept_children: bool = True,
        repr_: Optional[Union[str, float]] = None,
        data: Any = None,
    ) -> None:
        """
        :param identifier: node identifier, must be unique per tree
        """
        if identifier is None:
            if not auto_uuid:
                raise ValueError("Required identifier")
            identifier = str(uuid.uuid4())
        self.identifier = identifier
        self.keyed = keyed
        self.accept_children = accept_children
        self.repr = str(repr_) if repr_ is not None else None
        self.data = data

    def line_repr(self, depth: int, **kwargs: Any) -> Tuple[str, str]:
        """Control how node is displayed in tree representation.
        _
        ├── one                                           end
        │   └── two                                     myEnd
        └── three
        """
        if self.repr is not None:
            return self.repr, ""
        if not self.accept_children:
            return str(self.data), ""
        if self.keyed:
            return "{}", ""
        return "[]", ""

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.identifier == other.identifier

    def __str__(self) -> str:
        return "%s, id=%s" % (self.__class__.__name__, self.identifier)

    def __repr__(self) -> str:
        return self.__str__()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import copy
from future.utils import python_2_unicode_compatible, string_types, text_type
import uuid


@python_2_unicode_compatible
class Node(object):
    def __init__(
        self,
        identifier=None,
        auto_uuid=True,
        keyed=True,
        accept_children=True,
        repr_=None,
        data=None,
    ):
        """
        :param identifier: node identifier, must be unique per tree
        """
        if identifier is not None and not isinstance(identifier, string_types):
            raise ValueError(
                "Identifier must be a string type, provided type is <%s>"
                % type(identifier)
            )
        if identifier is None:
            if not auto_uuid:
                raise ValueError("Required identifier")
            identifier = uuid.uuid4()
        self.identifier = identifier
        self.keyed = keyed
        self.accept_children = accept_children
        self.repr = repr_
        self.data = data

    def line_repr(self, depth, **kwargs):
        """Control how node is displayed in tree representation.

        _
        ├── one                                           end
        │   └── two                                     myEnd
        └── three
        """
        if self.repr is not None:
            return self.repr, ""
        if not self.accept_children:
            return text_type(self.data), ""
        if self.keyed:
            return "{}", ""
        return "[]", ""

    def clone(self, deep=False):
        return copy.deepcopy(self) if deep else copy.copy(self)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.identifier == other.identifier

    def __str__(self):
        return "%s, id=%s" % (self.__class__.__name__, self.identifier)

    def __repr__(self):
        return self.__str__()

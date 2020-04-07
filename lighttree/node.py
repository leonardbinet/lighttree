#!/usr/bin/env python

from __future__ import unicode_literals
from future.utils import python_2_unicode_compatible, string_types

import uuid


@python_2_unicode_compatible
class Node(object):
    def __init__(self, identifier=None, auto_uuid=False):
        """
        :param identifier: node identifier, must be unique per tree
        """
        if not isinstance(identifier, string_types):
            raise ValueError(
                "Identifier must be a string type, provided type is <%s>"
                % type(identifier)
            )
        if identifier is None:
            if not auto_uuid:
                raise ValueError("Required identifier")
            identifier = uuid.uuid4()
        self.identifier = identifier

    def line_repr(self, **kwargs):
        """Control how node is displayed in tree representation.
        """
        return self.identifier

    def serialize(self, *args, **kwargs):
        return {"identifier": self.identifier}

    @classmethod
    def deserialize(cls, d, *args, **kwargs):
        if not isinstance(d, dict):
            raise ValueError("Deserialization requires a dict.")
        return cls._deserialize(d, *args, **kwargs)

    @classmethod
    def _deserialize(cls, d, *args, **kwargs):
        return cls(d.get("identifier"))

    def __str__(self):
        return "%s, id=%s" % (self.__class__.__name__, self.identifier)

    def __repr__(self):
        return self.__str__()

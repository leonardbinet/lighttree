#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import unicodedata

from typing import Optional, Union, List, Any, Dict
from lighttree.tree import Tree


def is_valid_attr_name(item) -> bool:
    if not isinstance(item, str):
        return False
    if item.startswith("__"):
        return False
    if re.search(string=item, pattern=r"^[a-zA-Z_]+[a-zA-Z0-9_]*$") is None:
        return False
    if re.search(string=item, pattern=r"[^_]") is None:
        return False
    return True


def _coerce_attr(attr) -> Union[str, None]:
    if not len(attr):
        return None
    new_attr = unicodedata.normalize("NFD", attr).encode("ASCII", "ignore").decode()
    new_attr = re.sub(string=new_attr, pattern=r"[^a-zA-Z_0-9]", repl="_")
    if new_attr[0].isdigit():
        new_attr = "_" + new_attr
    if is_valid_attr_name(new_attr):
        return new_attr
    return None


class Obj(object):
    """Object class that allows to get items both by attribute `__getattribute__` access: `obj.attribute` or by dict
    `__getitem__` access:
    >>> obj = Obj(key='value')
    >>> obj.key
    'value'
    >>> obj['key']
    'value'

    In Ipython interpreter, attributes will be available in autocomplete (except private ones):
    >>> obj = Obj(key='value', key2='value2')
    >>> obj.k  # press tab for autocompletion
    key
    key2

    Items names that are not compliant with python attributes (accepted characters are [a-zA-Z0-9\_] without beginning
    with a figure), will be only available through dict `__getitem__` access.
    """

    _REPR_NAME = None
    _STRING_KEY_CONSTRAINT = True
    _COERCE_ATTR = False

    def __init__(self, **kwargs) -> None:
        # will store non-valid names
        self.__d: Dict[str, Any] = dict()
        for k, v in kwargs.items():
            if not (
                isinstance(k, str)
                and k not in ("_REPR_NAME", "_Obj__d")
                and not k.startswith("__")
            ):
                raise ValueError(
                    "Attribute <%s> of type <%s> is not valid." % (k, type(k))
                )
            self[k] = v

    def __getitem__(self, item):
        # when calling d[key]
        if is_valid_attr_name(item):
            return self.__getattribute__(item)
        else:
            return self.__d[item]

    def __setitem__(self, key, value):
        # d[key] = value
        if not isinstance(key, str):
            if self._STRING_KEY_CONSTRAINT:
                raise ValueError(
                    "Key <%s> of type <%s> cannot be set as attribute on <%s> instance."
                    % (key, type(key), self.__class__.__name__)
                )
            self.__d[key] = value
            return
        if not is_valid_attr_name(key):
            self.__d[key] = value
            if self._COERCE_ATTR:
                # if coerc_attr is set to True, try to coerce
                n_key = _coerce_attr(key)
                if n_key is not None:
                    super(Obj, self).__setattr__(n_key, value)
        else:
            super(Obj, self).__setattr__(key, value)

    def __keys(self) -> List[Any]:
        return list(self.__d.keys()) + [
            k for k in self.__dict__.keys() if k not in ("_REPR_NAME", "_Obj__d")
        ]

    def __contains__(self, item) -> bool:
        return item in self.__keys()

    def __str__(self) -> str:
        return "<%s> %s" % (
            str(self.__class__._REPR_NAME or self.__class__.__name__),
            str(sorted(map(str, self.__keys()))),
        )

    def __repr__(self) -> str:
        return self.__str__()


class TreeBasedObj(Obj):
    """
    Recursive Obj whose structure is defined by a lighttree.Tree object.

    The main purpose of this object is to iteratively expand the tree as attributes of this object. To avoid creating
    useless instances, only direct children of accessed nodes are expanded.
    """

    _COERCE_ATTR = False
    _ATTR = None

    def __init__(
        self,
        tree: Tree,
        root_path: Optional[str] = None,
        depth: int = 1,
        initial_tree: Optional[Tree] = None,
    ) -> None:
        super(TreeBasedObj, self).__init__()
        self._tree = tree
        self._root_path = root_path
        self._initial_tree = initial_tree if initial_tree is not None else tree
        self._expand_attrs(depth)

    def _clone(self, nid: str, root_path: str, depth: int) -> "TreeBasedObj":
        _, st = self._tree.subtree(nid)
        return self.__class__(
            tree=st,
            root_path=root_path,
            depth=depth,
            initial_tree=self._initial_tree,
        )

    def _expand_attrs(self, depth: int) -> None:
        if depth:
            r = self._tree.root
            if r is None:
                return
            for child_key, child_node in self._tree.children(nid=r):
                if self._ATTR:
                    child_key = getattr(child_node, self._ATTR)
                str_child_key: str
                if isinstance(child_key, str):
                    if self._COERCE_ATTR:
                        # if invalid coercion, coerce returns None, in this case we keep inital naming
                        str_child_key = _coerce_attr(child_key) or child_key
                    else:
                        str_child_key = child_key
                else:
                    str_child_key = "i%s" % child_key

                child_root: str
                if self._root_path is not None:
                    child_root = "%s.%s" % (self._root_path, child_key)
                else:
                    child_root = str(child_key) if child_key else ""
                self[str_child_key] = self._clone(
                    child_node.identifier, root_path=child_root, depth=depth - 1
                )

    def __getattribute__(self, item):
        # called by __getattribute__ will always refer to valid attribute item
        r = super(TreeBasedObj, self).__getattribute__(item)
        if isinstance(r, TreeBasedObj):
            r._expand_attrs(depth=1)
        return r

    def __getitem__(self, item):
        if is_valid_attr_name(item):
            r = super(TreeBasedObj, self).__getattribute__(item)
        else:
            r = super(TreeBasedObj, self).__getitem__(item)
        if isinstance(r, TreeBasedObj):
            r._expand_attrs(depth=1)
        return r

    def _show(self, *args, **kwargs) -> str:
        tree_repr = self._tree.show(*args, **kwargs)
        if self._root_path is None:
            return "<%s>\n%s" % (
                str(self.__class__._REPR_NAME or self.__class__.__name__),
                str(tree_repr),
            )
        current_path = self._root_path
        return "<%s subpart: %s>\n%s" % (
            str(self.__class__._REPR_NAME or self.__class__.__name__),
            str(current_path),
            str(tree_repr),
        )

    def __call__(self, *args, **kwargs) -> Tree:
        return self._tree

    def __str__(self) -> str:
        return self._show()

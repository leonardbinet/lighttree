#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from future.utils import string_types, iteritems
from lighttree import Tree, Node


def tree_sanity_check(tree):
    assert isinstance(tree, Tree)
    assert isinstance(tree._nodes_map, dict)
    assert isinstance(tree._nodes_parent, dict)
    assert isinstance(tree._nodes_children, dict)

    assert all(nid in tree._nodes_map.keys() for nid in tree._nodes_parent.keys())
    assert all(nid in tree._nodes_map.keys() for nid in tree._nodes_children.keys())

    for nid, node in iteritems(tree._nodes_map):
        assert isinstance(nid, string_types)
        # ensure all nodes except root have a parent, and that it they are registered as child of that parent
        pid = tree._nodes_parent[nid]
        if nid == tree.root:
            assert pid is None
        else:
            assert pid is not None
            assert nid in tree._nodes_children[pid]
        # ensure all children have this node registered as parent
        for cid in tree._nodes_children[nid]:
            assert tree._nodes_parent[cid] == nid


# testing samples


def get_sample_tree():
    """
    root
    ├── a
    │   ├── a1
    │   │   ├── a11
    │   │   └── a12
    │   └── a2
    └── b
        └── b1
    """
    t = Tree()
    t.insert_node(Node(identifier="root"))
    t.insert_node(Node(identifier="a"), parent_id="root")
    t.insert_node(Node(identifier="a1"), parent_id="a")
    t.insert_node(Node(identifier="a2"), parent_id="a")
    t.insert_node(Node(identifier="a11"), parent_id="a1")
    t.insert_node(Node(identifier="a12"), parent_id="a1")
    t.insert_node(Node(identifier="b"), parent_id="root")
    t.insert_node(Node(identifier="b1"), parent_id="b")
    tree_sanity_check(t)
    return t


def get_sample_tree_2():
    """
    c
    ├── c1
    │   └── c12
    └── c2
    """
    t = Tree()
    t.insert_node(Node("c"))
    t.insert_node(Node("c1"), parent_id="c")
    t.insert_node(Node("c12"), parent_id="c1")
    t.insert_node(Node("c2"), parent_id="c")
    return t


def get_sample_custom_tree():
    """
    root, key=10
    ├── a, key=11
    │   ├── a1, key=12
    │   │   ├── a11, key=14
    │   │   └── a12, key=15
    │   └── a2, key=13
    └── b, key=1
        └── b1, key=2
    """
    t = TreeWithComposition(is_cool=True, mutable_object=[1, 2])
    t.insert_node(CustomNode(identifier="root", key=10))
    t.insert_node(CustomNode(identifier="a", key=11), parent_id="root")
    t.insert_node(CustomNode(identifier="a1", key=12), parent_id="a")
    t.insert_node(CustomNode(identifier="a2", key=13), parent_id="a")
    t.insert_node(CustomNode(identifier="a11", key=14), parent_id="a1")
    t.insert_node(CustomNode(identifier="a12", key=15), parent_id="a1")
    t.insert_node(CustomNode(identifier="b", key=1), parent_id="root")
    t.insert_node(CustomNode(identifier="b1", key=2), parent_id="b")
    tree_sanity_check(t)
    return t


class CustomNode(Node):
    def __init__(self, identifier, key):
        self.key = key
        super(CustomNode, self).__init__(identifier=identifier)

    def clone(self, deep=False):
        return self.__class__(identifier=self.identifier, key=self.key,)

    def serialize(self, *args, **kwargs):
        with_key = kwargs.pop("with_key", None)
        d = super(CustomNode, self).serialize()
        if with_key:
            d["key"] = self.key
        return d

    @classmethod
    def _deserialize(cls, d, *args, **kwargs):
        return cls(identifier=d.get("identifier"), key=d.get("key"))

    def line_repr(self, depth, **kwargs):
        if kwargs.get("with_key"):
            return "%s, key=%s" % (self.identifier, self.key)
        return self.identifier


class TreeWithComposition(Tree):

    node_class = CustomNode

    def __init__(self, is_cool, mutable_object):
        self.is_cool = is_cool
        self.mutable_object = mutable_object
        super(TreeWithComposition, self).__init__()

    def _clone_init(self, deep):
        return TreeWithComposition(
            is_cool=self.is_cool,
            mutable_object=copy.deepcopy(self.mutable_object)
            if deep
            else self.mutable_object,
        )

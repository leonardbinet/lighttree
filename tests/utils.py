#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lighttree import Tree, Node
from future.utils import string_types, iteritems


def tree_sanity_check(tree):
    assert isinstance(tree, Tree)
    assert issubclass(tree.node_class, Node)
    assert isinstance(tree._nodes_map, dict)
    assert isinstance(tree._nodes_parent, dict)
    assert isinstance(tree._nodes_children, dict)

    assert all(nid in tree._nodes_map.keys() for nid in tree._nodes_parent.keys())
    assert all(nid in tree._nodes_map.keys() for nid in tree._nodes_children.keys())

    for nid, node in iteritems(tree._nodes_map):
        assert isinstance(nid, string_types)
        assert isinstance(node, tree.node_class)
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from future.utils import string_types, iteritems
from lighttree import Tree, Node


def tree_sanity_check(tree):
    assert isinstance(tree, Tree)
    assert isinstance(tree._nodes_map, dict)
    assert isinstance(tree._nodes_parent, dict)
    assert isinstance(tree._nodes_children_list, dict)

    assert all(nid in tree._nodes_map.keys() for nid in tree._nodes_parent.keys())
    assert all(
        nid in tree._nodes_map.keys() for nid in tree._nodes_children_list.keys()
    )

    for nid, node in iteritems(tree._nodes_map):
        assert isinstance(nid, string_types)
        # ensure all nodes except root have a parent, and that it they are registered as child of that parent
        pid = tree._nodes_parent[nid]
        if nid == tree.root:
            assert pid is None
        else:
            assert pid is not None
            if tree._nodes_map[pid].keyed:
                assert nid in tree._nodes_children_map[pid]
                # ensure key is string
                assert isinstance(tree._nodes_children_map[pid][nid], string_types)
            else:
                assert nid in tree._nodes_children_list[pid]
        # ensure all children have this node registered as parent
        if node.keyed:
            for cid in tree._nodes_children_map[nid].keys():
                assert tree._nodes_parent[cid] == nid
        else:
            for cid in tree._nodes_children_list[nid]:
                assert tree._nodes_parent[cid] == nid


# testing samples


def get_sample_tree(path_separator="."):
    """
    root {}
    ├── a {}
    │   ├── aa []
    │   │   ├── aa0
    │   │   └── aa1
    │   └── ab {}
    └── c []
        ├── c0
        └── c1
    """
    t = Tree(path_separator=path_separator)
    t.insert_node(Node(identifier="root"))
    t.insert_node(Node(identifier="a"), parent_id="root", key="a")
    t.insert_node(Node(identifier="aa", keyed=False), parent_id="a", key="a")
    t.insert_node(Node(identifier="aa0", repr_="AA0"), parent_id="aa")
    t.insert_node(Node(identifier="aa1", repr_="AA1"), parent_id="aa")
    t.insert_node(Node(identifier="ab"), parent_id="a", key="b")
    t.insert_node(Node(identifier="c", keyed=False), parent_id="root", key="c")
    t.insert_node(Node(identifier="c0", repr_="C0"), parent_id="c")
    t.insert_node(Node(identifier="c1", repr_="C1"), parent_id="c")

    tree_sanity_check(t)
    return t


def get_sample_tree_2():
    """
    broot []
    ├── b1 {}
    │   └── b1a {}
    └── b2 {}
    """
    t = Tree()
    t.insert_node(Node("broot", keyed=False))
    t.insert_node(Node("b1"), parent_id="broot")
    t.insert_node(Node("b1a"), parent_id="b1", key="a")
    t.insert_node(Node("b2"), parent_id="broot")
    return t

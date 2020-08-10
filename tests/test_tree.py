#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from operator import attrgetter
from collections import defaultdict
from unittest import TestCase


from lighttree import Tree, Node
from lighttree.exceptions import (
    MultipleRootError,
    NotFoundNodeError,
    DuplicatedNodeError,
)
from tests.testing_utils import (
    tree_sanity_check,
    get_sample_tree,
    get_sample_tree_2,
    get_sample_custom_tree,
    TreeWithComposition,
)
from future.utils import iteritems


def to_ids_set(nodes):
    return {n.identifier for n in nodes}


class TreeCase(TestCase):
    def assertDefaultDictEqual(self, first, second, msg=None):
        """Assert that two items are defaultdict, and that they have same content, ignoring default values."""
        self.assertIsInstance(first, defaultdict, msg)
        self.assertIsInstance(second, defaultdict, msg)
        self.assertEqual(first.default_factory(), second.default_factory(), msg)
        for key in set(first.keys()) | set(second.keys()):
            self.assertEqual(first[key], second[key])

    def test_insert_root(self):
        t = Tree()
        root_node = Node(identifier="a")
        t._insert_node_below(root_node, None)
        self.assertSetEqual(to_ids_set(t.list()), {"a"})
        self.assertIs(t._nodes_map["a"], root_node)
        self.assertEqual(t._nodes_parent["a"], None)
        self.assertSetEqual(t._nodes_children["a"], set())
        tree_sanity_check(t)

        # cannot add second root
        with self.assertRaises(MultipleRootError):
            t._insert_node_below(Node(identifier="b"), None)
        self.assertSetEqual(to_ids_set(t.list()), {"a"})
        tree_sanity_check(t)

        # wrong node insertion
        with self.assertRaises(ValueError):
            Tree().insert_node({"key": "a"})

    def test_insert_node_below(self):
        t = Tree()
        t.insert_node(Node("root_id"))

        # cannot insert under not existing parent
        with self.assertRaises(NotFoundNodeError):
            t.insert_node(Node(identifier="a"), parent_id="what")
        tree_sanity_check(t)

        # insert node below another one
        node_a = Node("a")
        t.insert_node(node_a, parent_id="root_id")
        self.assertSetEqual(set(t._nodes_map.keys()), {"root_id", "a"})
        self.assertEqual(t._nodes_map["a"], node_a)
        self.assertEqual(t._nodes_parent["root_id"], None)
        self.assertEqual(t._nodes_parent["a"], "root_id")
        self.assertSetEqual(t._nodes_children["a"], set())
        self.assertSetEqual(t._nodes_children["root_id"], {"a"})
        tree_sanity_check(t)

        # try to insert node with same id than existing node
        with self.assertRaises(DuplicatedNodeError):
            t.insert_node(Node("a"), parent_id="root_id")
        tree_sanity_check(t)

    def test_insert_node_above(self):
        # above root
        t = Tree()
        t.insert_node(Node("initial_root"))
        t.insert_node(node=Node("new_root"), child_id="initial_root")
        self.assertEqual(t.root, "new_root")
        tree_sanity_check(t)
        self.assertEqual(
            t.show(),
            """new_root
└── initial_root
""",
        )

        # above node
        t = get_sample_tree()
        t.insert_node(Node("new"), child_id="a1")
        self.assertTrue("new" in t)
        self.assertEqual(
            t.show(),
            """root
├── a
│   ├── a2
│   └── new
│       └── a1
│           ├── a11
│           └── a12
└── b
    └── b1
""",
        )
        tree_sanity_check(t)

    def test_validate_node_insertion(self):
        t = Tree()
        t.insert_node(Node("a"))

        # cannot insert node of wrong class
        class MyNotValidClass(object):
            pass

        with self.assertRaises(ValueError):
            t._validate_node_insertion(MyNotValidClass())
        with self.assertRaises(ValueError):
            t.insert_node({})

        # cannot add node with similar id
        with self.assertRaises(DuplicatedNodeError):
            t._validate_node_insertion(Node("a"))

    def test_contains(self):
        t = get_sample_tree()
        self.assertTrue("a12" in t)
        self.assertFalse("yolo_id" in t)

    def test_get(self):
        t = get_sample_tree()
        with self.assertRaises(NotFoundNodeError):
            t.get("not_existing_id")
        self.assertIs(t.get("a"), t._nodes_map["a"])

    def test_list(self):
        t = get_sample_tree()

        self.assertEqual(to_ids_set(t.list(id_in=["a", "b"])), {"a", "b"})
        self.assertEqual(
            to_ids_set(t.list(depth_in=[0, 2])), {"root", "a1", "a2", "b1"}
        )
        self.assertEqual(to_ids_set(t.list(id_in=["a", "a1"], depth_in=[1])), {"a"})

        t2 = get_sample_custom_tree()
        self.assertEqual(
            to_ids_set(t2.list(filter_=lambda x: x.key > 5)),
            {"a11", "a1", "root", "a12", "a2", "a"},
        )
        self.assertEqual(
            to_ids_set(t2.list(id_in=["a", "b"], filter_=lambda x: x.key > 5)), {"a"}
        )

    def test_is_empty(self):
        self.assertTrue(Tree().is_empty())
        t = get_sample_tree()
        self.assertFalse(t.is_empty())

    def test_ensure_present(self):
        t = get_sample_tree()

        # existing node id
        self.assertEqual(
            t._ensure_present("a", defaults_to_root=False, allow_empty=False), "a"
        )
        self.assertEqual(
            t._ensure_present("a", defaults_to_root=True, allow_empty=False), "a"
        )
        self.assertEqual(
            t._ensure_present("a", defaults_to_root=False, allow_empty=True), "a"
        )
        self.assertEqual(
            t._ensure_present("a", defaults_to_root=True, allow_empty=True), "a"
        )

        # non-existing node id
        with self.assertRaises(NotFoundNodeError):
            t._ensure_present("fake_id", defaults_to_root=False, allow_empty=False)
        with self.assertRaises(NotFoundNodeError):
            t._ensure_present("fake_id", defaults_to_root=True, allow_empty=False)
        with self.assertRaises(NotFoundNodeError):
            t._ensure_present("fake_id", defaults_to_root=False, allow_empty=True)
        with self.assertRaises(NotFoundNodeError):
            t._ensure_present("fake_id", defaults_to_root=True, allow_empty=True)

        # None on non-empty tree
        with self.assertRaises(ValueError):
            t._ensure_present(None, defaults_to_root=False, allow_empty=False)
        self.assertEqual(
            t._ensure_present(None, defaults_to_root=True, allow_empty=False), "root"
        )
        self.assertEqual(
            t._ensure_present(None, defaults_to_root=False, allow_empty=True), None
        )
        self.assertEqual(
            t._ensure_present(None, defaults_to_root=True, allow_empty=True), "root"
        )

        # None on empty tree
        empty_tree = Tree()
        with self.assertRaises(ValueError):
            empty_tree._ensure_present(None, defaults_to_root=False, allow_empty=False)
        with self.assertRaises(ValueError):
            self.assertEqual(
                empty_tree._ensure_present(
                    None, defaults_to_root=True, allow_empty=False
                ),
                "root",
            )
        self.assertEqual(
            empty_tree._ensure_present(None, defaults_to_root=False, allow_empty=True),
            None,
        )
        self.assertEqual(
            empty_tree._ensure_present(None, defaults_to_root=True, allow_empty=True),
            None,
        )

    def test_clone_with_tree(self):
        t = get_sample_custom_tree()

        # deep = False
        t_shallow_clone = t.clone(with_tree=True)
        self.assertIsInstance(t_shallow_clone, TreeWithComposition)
        self.assertIsNot(t_shallow_clone, t)
        self.assertFalse(t_shallow_clone.is_empty())
        self.assertIsNot(t_shallow_clone._nodes_map, t._nodes_map)
        self.assertEqual(t_shallow_clone._nodes_map, t._nodes_map)
        self.assertIsNot(t_shallow_clone._nodes_parent, t._nodes_parent)
        self.assertDefaultDictEqual(t_shallow_clone._nodes_parent, t._nodes_parent)
        self.assertIsNot(t_shallow_clone._nodes_children, t._nodes_children)
        self.assertDefaultDictEqual(t_shallow_clone._nodes_children, t._nodes_children)
        # based on TreeWithComposition._clone_init method
        self.assertTrue(t_shallow_clone.is_cool)
        self.assertIs(t.mutable_object, t_shallow_clone.mutable_object)
        # nodes are shallow copies
        for nid, node in iteritems(t._nodes_map):
            self.assertEqual(t_shallow_clone._nodes_map[nid], node)
        tree_sanity_check(t)
        tree_sanity_check(t_shallow_clone)

        # deep = True
        t_custom_deep_clone = t.clone(with_tree=True, deep=True)
        self.assertIsNot(t.mutable_object, t_custom_deep_clone.mutable_object)
        # nodes are deep copies
        for nid, node in iteritems(t_custom_deep_clone._nodes_map):
            self.assertIsNot(t._nodes_map[nid], node)

    def test_clone_with_subtree(self):
        t = get_sample_custom_tree()

        t_clone = t.clone(with_tree=True, new_root="a")
        self.assertIsInstance(t_clone, TreeWithComposition)
        self.assertIsNot(t_clone, t)
        self.assertFalse(t_clone.is_empty())
        self.assertSetEqual(
            set(t_clone._nodes_map.keys()), {"a", "a1", "a2", "a11", "a12"}
        )
        self.assertDefaultDictEqual(
            t_clone._nodes_parent,
            defaultdict(
                lambda: None,
                {"a": None, "a1": "a", "a2": "a", "a11": "a1", "a12": "a1"},
            ),
        )
        self.assertDefaultDictEqual(
            t_clone._nodes_children,
            defaultdict(
                set,
                {
                    "a": {"a1", "a2"},
                    "a1": {"a11", "a12"},
                    "a2": set(),
                    "a11": set(),
                    "a12": set(),
                },
            ),
        )

        # based on TreeWithComposition._clone_init method
        self.assertTrue(t_clone.is_cool)
        self.assertIs(t.mutable_object, t_clone.mutable_object)
        # nodes are shallow copies
        for nid, node in iteritems(t_clone._nodes_map):
            self.assertIs(t_clone._nodes_map[nid], node)
        tree_sanity_check(t)
        tree_sanity_check(t_clone)

    def test_empty_clone(self):
        t = get_sample_custom_tree()

        # deep = False
        t_shallow_empty_clone = t.clone(with_tree=False)
        self.assertIsInstance(t_shallow_empty_clone, TreeWithComposition)
        self.assertIsNot(t_shallow_empty_clone, t)
        self.assertTrue(t_shallow_empty_clone.is_empty())
        tree_sanity_check(t)
        tree_sanity_check(t_shallow_empty_clone)
        self.assertTrue(t.is_cool)
        self.assertEqual(t_shallow_empty_clone.mutable_object, [1, 2])
        # not a deepcopy
        self.assertIs(t.mutable_object, t_shallow_empty_clone.mutable_object)

        # empty clone with deep copy
        t_empty_deep_clone = t.clone(with_tree=False, deep=True)
        self.assertIsNot(t.mutable_object, t_empty_deep_clone.mutable_object)

    def test_parent(self):
        t = get_sample_tree()
        self.assertEqual(t.parent("root"), None)
        self.assertEqual(t.parent("a"), "root")
        self.assertEqual(t.parent("a1"), "a")
        self.assertEqual(t.parent("b1"), "b")
        with self.assertRaises(NotFoundNodeError):
            t.parent("non-existing-id")
        self.assertIs(t.parent("a", id_only=False), t._nodes_map["root"])

    def test_children(self):
        t = get_sample_tree()
        self.assertEqual(set(t.children("root")), {"a", "b"})
        self.assertEqual(set(t.children("a")), {"a1", "a2"})
        self.assertEqual(t.children("b"), ["b1"])
        self.assertEqual(set(t.children("a1")), {"a11", "a12"})
        self.assertEqual(t.children("b1"), [])
        with self.assertRaises(NotFoundNodeError):
            t.children("non-existing-id")
        self.assertIs(next(iter(t.children("b", id_only=False))), t._nodes_map["b1"])

    def test_siblings(self):
        t = get_sample_tree()
        self.assertEqual(t.siblings("root"), [])
        self.assertEqual(t.siblings("a"), ["b"])
        self.assertEqual(t.siblings("b"), ["a"])
        self.assertEqual(t.siblings("a1"), ["a2"])
        self.assertEqual(t.siblings("b1"), [])
        with self.assertRaises(NotFoundNodeError):
            t.siblings("non-existing-id")
        self.assertIs(next(iter(t.siblings("b", id_only=False))), t._nodes_map["a"])

    def test_is_leaf(self):
        t = get_sample_tree()
        self.assertFalse(t.is_leaf("root"))
        self.assertFalse(t.is_leaf("a"))
        self.assertFalse(t.is_leaf("b"))
        self.assertTrue(t.is_leaf("a11"))
        self.assertTrue(t.is_leaf("a12"))
        self.assertTrue(t.is_leaf("b1"))
        with self.assertRaises(NotFoundNodeError):
            t.is_leaf("non-existing-id")

    def test_depth(self):
        t = get_sample_tree()
        self.assertEqual(t.depth("root"), 0)
        self.assertEqual(t.depth("a"), 1)
        self.assertEqual(t.depth("b"), 1)
        self.assertEqual(t.depth("a1"), 2)
        self.assertEqual(t.depth("a2"), 2)
        self.assertEqual(t.depth("b1"), 2)
        with self.assertRaises(NotFoundNodeError):
            t.depth("non-existing-id")

    def test_ancestors(self):
        t = get_sample_tree()
        self.assertEqual(t.ancestors("root"), [])
        self.assertEqual(t.ancestors("a"), ["root"])
        self.assertEqual(t.ancestors("b"), ["root"])
        self.assertEqual(t.ancestors("a1"), ["a", "root"])
        self.assertEqual(t.ancestors("a1", from_root=True), ["root", "a"])
        self.assertEqual(t.ancestors("a2"), ["a", "root"])
        self.assertEqual(t.ancestors("a2", from_root=True), ["root", "a"])
        self.assertEqual(t.ancestors("b1"), ["b", "root"])
        self.assertEqual(t.ancestors("b1", from_root=True), ["root", "b"])

        with self.assertRaises(NotFoundNodeError):
            t.ancestors("non-existing-id")

    def test_leaves(self):
        t = get_sample_tree()
        self.assertEqual(set(t.leaves()), {"a11", "a12", "a2", "b1"})
        self.assertEqual(set(t.leaves("a")), {"a11", "a12", "a2"})
        self.assertEqual(t.leaves("a11"), ["a11"])
        self.assertEqual(t.leaves("b"), ["b1"])

    def test_expand_tree(self):
        t = get_sample_custom_tree()

        # depth mode
        self.assertEqual(
            list(t.expand_tree()), ["root", "a", "a1", "a11", "a12", "a2", "b", "b1"]
        )
        self.assertEqual(
            list(t.expand_tree(reverse=True)),
            ["root", "b", "b1", "a", "a2", "a1", "a12", "a11"],
        )
        # b's keys are lower (0 vs 1 for a's keys)
        self.assertEqual(
            list(t.expand_tree(key=attrgetter("key"))),
            ["root", "b", "b1", "a", "a1", "a11", "a12", "a2"],
        )
        self.assertEqual(
            list(t.expand_tree(key=attrgetter("key"), reverse=True)),
            ["root", "a", "a2", "a1", "a12", "a11", "b", "b1"],
        )
        # subtree
        self.assertEqual(list(t.expand_tree(nid="a")), ["a", "a1", "a11", "a12", "a2"])

        # width mode
        self.assertEqual(
            list(t.expand_tree(mode="width")),
            ["root", "a", "b", "a1", "a2", "b1", "a11", "a12"],
        )
        self.assertEqual(
            list(t.expand_tree(mode="width", reverse=True)),
            ["root", "b", "a", "b1", "a2", "a1", "a12", "a11"],
        )
        # b's keys are lower (0 vs 1 for a's keys)
        self.assertEqual(
            list(t.expand_tree(mode="width", key=attrgetter("key"))),
            ["root", "b", "a", "b1", "a1", "a2", "a11", "a12"],
        )
        self.assertEqual(
            list(t.expand_tree(mode="width", key=attrgetter("key"), reverse=True)),
            ["root", "a", "b", "a2", "a1", "b1", "a12", "a11"],
        )
        # subtree
        self.assertEqual(
            list(t.expand_tree(nid="a", mode="width")), ["a", "a1", "a2", "a11", "a12"]
        )

        # filter
        self.assertEqual(
            list(t.expand_tree(filter_=lambda x: x.identifier in ("root", "b"))),
            ["root", "b"],
        )

        # without filter through
        self.assertEqual(list(t.expand_tree(filter_=lambda x: "2" in x.identifier)), [])
        # with filter through
        self.assertEqual(
            list(
                t.expand_tree(
                    filter_=lambda x: "2" in x.identifier, filter_through=True
                )
            ),
            ["a12", "a2"],
        )

    def test_iter_nodes_with_location(self):
        t = get_sample_tree()

        # full
        self.assertEqual(
            list(
                t._iter_nodes_with_location(
                    nid=None, filter_=None, key=None, reverse=False
                )
            ),
            [
                ((), t.get("root")),
                ((False,), t.get("a")),
                ((False, False), t.get("a1")),
                ((False, False, False), t.get("a11")),
                ((False, False, True), t.get("a12")),
                ((False, True), t.get("a2")),
                ((True,), t.get("b")),
                ((True, True), t.get("b1")),
            ],
        )
        self.assertEqual(
            t.show(),
            """root
├── a
│   ├── a1
│   │   ├── a11
│   │   └── a12
│   └── a2
└── b
    └── b1
""",
        )

        # subtree
        self.assertEqual(
            list(
                t._iter_nodes_with_location(
                    nid="a1", filter_=None, key=None, reverse=False
                )
            ),
            [((), t.get("a1")), ((False,), t.get("a11")), ((True,), t.get("a12"))],
        )
        self.assertEqual(
            t.show("a1"),
            """a1
├── a11
└── a12
""",
        )

    def test_show(self):
        t = get_sample_custom_tree()
        self.assertEqual(
            t.show(),
            """root
├── a
│   ├── a1
│   │   ├── a11
│   │   └── a12
│   └── a2
└── b
    └── b1
""",
        )
        self.assertEqual(
            t.show(with_key=True),
            """root, key=10
├── a, key=11
│   ├── a1, key=12
│   │   ├── a11, key=14
│   │   └── a12, key=15
│   └── a2, key=13
└── b, key=1
    └── b1, key=2
""",
        )

        # limit number of displayed nodes
        self.assertEqual(
            t.show(limit=3),
            """root
├── a
│   ├── a1
...
(truncated, total number of nodes: 8)
""",
        )

    def test_prefix_repr(self):
        self.assertEqual(Tree._prefix_repr(line_type="ascii-ex", is_last_list=[]), "")
        self.assertEqual(
            Tree._prefix_repr(line_type="ascii-ex", is_last_list=[True]), "└── "
        )
        self.assertEqual(
            Tree._prefix_repr(line_type="ascii-ex", is_last_list=[False]), "├── "
        )
        self.assertEqual(
            Tree._prefix_repr(line_type="ascii-ex", is_last_list=[True, False, True]),
            "    │   └── ",
        )
        self.assertEqual(
            Tree._prefix_repr(line_type="ascii-ex", is_last_list=[False, False, False]),
            "│   │   ├── ",
        )

    def test_insert_tree_below(self):
        t = get_sample_tree()

        # cannot insert tree not instance of initial tree
        with self.assertRaises(ValueError):
            t_custom = get_sample_custom_tree()
            t_custom._insert_tree_below(get_sample_tree(), "a1", False)
        tree_sanity_check(t_custom)

        # insert subtree
        t_to_paste = get_sample_tree_2()
        t._insert_tree_below(new_tree=t_to_paste, parent_id="b", deep=False)
        tree_sanity_check(t)
        tree_sanity_check(t_to_paste)
        self.assertEqual(
            t.show(),
            """root
├── a
│   ├── a1
│   │   ├── a11
│   │   └── a12
│   └── a2
└── b
    ├── b1
    └── c
        ├── c1
        │   └── c12
        └── c2
""",
        )
        self.assertTrue(all(nid in t for nid in ("c", "c1", "c2", "c12")))
        # by default pasted new tree is a shallow copy
        self.assertEqual(t.get("c"), t_to_paste.get("c"))

        # cannot repaste tree, because then there would be node duplicates
        with self.assertRaises(DuplicatedNodeError):
            t._insert_tree_below(new_tree=t_to_paste, parent_id="a2", deep=False)
        tree_sanity_check(t)
        tree_sanity_check(t_to_paste)

        # with deep copy, new tree nodes are a deepcopy
        t2 = get_sample_tree()
        t2_to_paste = get_sample_tree_2()
        t2._insert_tree_below(t2_to_paste, "b", deep=True)
        tree_sanity_check(t2)
        tree_sanity_check(t2_to_paste)
        self.assertEqual(
            t2.show(),
            """root
├── a
│   ├── a1
│   │   ├── a11
│   │   └── a12
│   └── a2
└── b
    ├── b1
    └── c
        ├── c1
        │   └── c12
        └── c2
""",
        )
        self.assertIsNot(t2.get("c"), t2_to_paste.get("c"))

    def test_insert_tree_at_root(self):
        t = Tree()
        t.insert_tree(get_sample_tree())
        tree_sanity_check(t)
        self.assertEqual(
            t.show(),
            """root
├── a
│   ├── a1
│   │   ├── a11
│   │   └── a12
│   └── a2
└── b
    └── b1
""",
        )

        # cannot insert at root if already present root
        t = Tree()
        t.insert_node(Node("present_root"))
        with self.assertRaises(MultipleRootError):
            t.insert_tree(get_sample_tree())
        tree_sanity_check(t)

    def test_insert_tree_above(self):
        t = get_sample_tree()

        # cannot insert subtree above if inserted tree has multiple leaves, and without specifying under which new tree
        # node existing children should be placed
        with self.assertRaises(ValueError):
            t.insert_tree(get_sample_tree_2(), child_id="a1")
        self.assertTrue(all(nid not in t for nid in {"c", "c1", "c2", "c12"}))
        tree_sanity_check(t)

        # insert subtree with proper specification
        t.insert_tree(get_sample_tree_2(), child_id="a1", child_id_below="c2")
        tree_sanity_check(t)
        self.assertTrue(all(nid in t for nid in {"c", "c1", "c2", "c12"}))
        self.assertEqual(
            t.show(),
            """root
├── a
│   ├── a2
│   └── c
│       ├── c1
│       │   └── c12
│       └── c2
│           └── a1
│               ├── a11
│               └── a12
└── b
    └── b1
""",
        )

        # insert subtree, without proper child specification, but with only one leaf will by default place children
        # below that leaf
        t = get_sample_tree()
        t2 = get_sample_tree_2()
        t2.drop_node("c2")
        t.insert_tree(t2, child_id="a1")
        tree_sanity_check(t)
        tree_sanity_check(t2)
        self.assertEqual(
            t.show(),
            """root
├── a
│   ├── a2
│   └── c
│       └── c1
│           └── c12
│               └── a1
│                   ├── a11
│                   └── a12
└── b
    └── b1
""",
        )

    def test_merge(self):
        t = get_sample_tree()

        # cannot merge tree not instance of initial tree
        with self.assertRaises(ValueError):
            t_custom = get_sample_custom_tree()
            t_custom.merge(get_sample_tree(), "a1")
        tree_sanity_check(t)

        t_to_merge = get_sample_tree_2()
        t.merge(new_tree=t_to_merge, nid="b")
        tree_sanity_check(t)
        tree_sanity_check(t_to_merge)
        self.assertEqual(
            t.show(),
            """root
├── a
│   ├── a1
│   │   ├── a11
│   │   └── a12
│   └── a2
└── b
    ├── b1
    ├── c1
    │   └── c12
    └── c2
""",
        )
        # new tree root is not conserved
        self.assertTrue("c" not in t)
        self.assertTrue(all(nid in t for nid in ("c1", "c2", "c12")))
        self.assertEqual(t.get("c1"), t_to_merge.get("c1"))

        # cannot remerge tree, because then there would be node duplicates
        with self.assertRaises(DuplicatedNodeError):
            t.merge(new_tree=t_to_merge, nid="a2")
        tree_sanity_check(t)
        tree_sanity_check(t_to_merge)

        # with deep copy, new tree nodes are a deepcopy
        t2 = get_sample_tree()
        t2_to_merge = get_sample_tree_2()
        t2.merge(t2_to_merge, "b", deep=True)
        tree_sanity_check(t2)
        tree_sanity_check(t2_to_merge)
        self.assertEqual(
            t2.show(),
            """root
├── a
│   ├── a1
│   │   ├── a11
│   │   └── a12
│   └── a2
└── b
    ├── b1
    ├── c1
    │   └── c12
    └── c2
""",
        )
        self.assertIsNot(t2.get("c1"), t2_to_merge.get("c1"))

        # merge on initial empty tree
        t = Tree()
        t.merge(get_sample_tree_2())
        tree_sanity_check(t)
        self.assertEqual(
            t.show(),
            """c
├── c1
│   └── c12
└── c2
""",
        )
        # in this case new_tree root is conserved since initial tree is empty
        self.assertTrue(all(nid in t for nid in ("c", "c1", "c2", "c12")))

    def test_drop_node(self):
        # drop with children
        t = get_sample_tree()
        a1_node = t.drop_node("a1")
        tree_sanity_check(t)
        self.assertIsInstance(a1_node, Node)
        self.assertEqual(a1_node.identifier, "a1")
        self.assertTrue(all(nid not in t for nid in ("a1", "a11", "a12")))
        self.assertEqual(
            t.show(),
            """root
├── a
│   └── a2
└── b
    └── b1
""",
        )

        # drop without children (rebase children to dropped node's parent)
        t2 = get_sample_tree()
        a1_node = t2.drop_node("a1", with_children=False)
        tree_sanity_check(t2)
        self.assertIsInstance(a1_node, Node)
        self.assertTrue(all(nid in t2 for nid in ("a11", "a12")))
        self.assertTrue("a1" not in t2)
        self.assertEqual(
            t2.show(),
            """root
├── a
│   ├── a11
│   ├── a12
│   └── a2
└── b
    └── b1
""",
        )

        # cannot drop root if it has multiple children
        t3 = get_sample_tree()
        with self.assertRaises(MultipleRootError):
            t3.drop_node("root", with_children=False)

    def test_drop_subtree(self):
        t = get_sample_tree()
        a1_subtree = t.drop_subtree("a1")
        self.assertIsInstance(a1_subtree, Tree)
        self.assertTrue(all(nid in a1_subtree for nid in ("a1", "a11", "a12")))
        self.assertTrue(all(nid not in t for nid in ("a1", "a11", "a12")))
        self.assertEqual(
            t.show(),
            """root
├── a
│   └── a2
└── b
    └── b1
""",
        )
        self.assertEqual(
            a1_subtree.show(),
            """a1
├── a11
└── a12
""",
        )

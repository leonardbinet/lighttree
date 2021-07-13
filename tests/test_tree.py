#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from collections import defaultdict
from operator import itemgetter
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
)


def to_key_id(keyed_nodes):
    return [(k, n.identifier) for k, n in keyed_nodes]


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
        t.insert_node(root_node)
        self.assertEqual(to_key_id(t.list()), [(None, "a")])
        self.assertIs(t._nodes_map["a"], root_node)
        self.assertEqual(t._nodes_parent["a"], None)
        self.assertListEqual(t._nodes_children_list["a"], list())
        self.assertEqual(t._nodes_children_map["a"], {})
        tree_sanity_check(t)

        # cannot add second root
        with self.assertRaises(MultipleRootError):
            t.insert_node(Node(identifier="b"))
        self.assertEqual(to_key_id(t.list()), [(None, "a")])
        tree_sanity_check(t)

        # wrong node insertion
        with self.assertRaises(AttributeError):
            Tree().insert_node({"key": "a"})

    def test_insert_node_below(self):
        t = Tree()
        t.insert_node(Node("root_id"))

        # cannot insert under not existing parent
        with self.assertRaises(NotFoundNodeError):
            t.insert_node(Node(identifier="a"), parent_id="what")
        tree_sanity_check(t)

        # insert node below another one
        node_a = Node("a_id")
        t.insert_node(node_a, parent_id="root_id", key="a")
        self.assertSetEqual(set(t._nodes_map.keys()), {"root_id", "a_id"})
        self.assertEqual(t._nodes_map["a_id"], node_a)
        self.assertEqual(t._nodes_parent["root_id"], None)
        self.assertEqual(t._nodes_parent["a_id"], "root_id")
        self.assertListEqual(t._nodes_children_list["a_id"], list())
        self.assertEqual(t._nodes_children_map["root_id"], {"a_id": "a"})
        tree_sanity_check(t)

        # try to insert node with same id than existing node
        with self.assertRaises(DuplicatedNodeError):
            t.insert_node(Node("a_id"), parent_id="root_id", key="b")
        tree_sanity_check(t)

    def test_insert_node_above(self):
        # above root
        t = Tree()
        t.insert_node(Node("initial_root"))
        t.insert_node(node=Node("new_root"), child_id="initial_root", key="between")
        self.assertEqual(t.root, "new_root")
        self.assertEqual(
            to_key_id(t.children("new_root")), [("between", "initial_root")]
        )
        tree_sanity_check(t)
        self.assertEqual(
            t.show(),
            """{}
└── between: {}
""",
        )

        # above node
        t = get_sample_tree()
        t.insert_node(Node("new"), child_id="aa0", key="to")
        self.assertTrue("new" in t)
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   ├── a: []
│   │   ├── {}
│   │   │   └── to: AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    └── C1
""",
        )
        tree_sanity_check(t)

    def test_validate_node_insertion(self):
        t = Tree()
        t.insert_node(Node("a"))

        # cannot insert node of wrong class
        class MyNotValidClass(object):
            pass

        with self.assertRaises(AttributeError):
            t._validate_node_insertion(MyNotValidClass())
        with self.assertRaises(AttributeError):
            t.insert_node({})

        # cannot add node with similar id
        with self.assertRaises(DuplicatedNodeError):
            t._validate_node_insertion(Node("a"))

    def test_contains(self):
        t = get_sample_tree()
        self.assertTrue("aa0" in t)
        self.assertFalse("yolo_id" in t)

    def test_get(self):
        t = get_sample_tree()
        with self.assertRaises(NotFoundNodeError):
            t.get("not_existing_id")
        k, n = t.get("ab")
        self.assertIs(n, t._nodes_map["ab"])
        self.assertEqual(k, "b")

        k, n = t.get("aa1")
        self.assertIs(n, t._nodes_map["aa1"])
        self.assertEqual(k, 1)

    def test_list(self):
        t = get_sample_tree()

        self.assertEqual(to_key_id(t.list(id_in=["a", "c"])), [("a", "a"), ("c", "c")])
        self.assertEqual(
            sorted(to_key_id(t.list(depth_in=[0, 2])), key=itemgetter(1)),
            sorted(
                [(None, "root"), ("a", "aa"), ("b", "ab"), (0, "c0"), (1, "c1")],
                key=itemgetter(1),
            ),
        )
        self.assertEqual(
            sorted(to_key_id(t.list(depth_in=[3])), key=itemgetter(1)),
            sorted([(0, "aa0"), (1, "aa1")], key=itemgetter(1)),
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
        t = get_sample_tree()

        # deep = False
        t_shallow_clone = t.clone(with_nodes=True)
        self.assertIsInstance(t_shallow_clone, Tree)
        self.assertIsNot(t_shallow_clone, t)
        self.assertFalse(t_shallow_clone.is_empty())
        self.assertIsNot(t_shallow_clone._nodes_map, t._nodes_map)
        self.assertEqual(t_shallow_clone._nodes_map, t._nodes_map)
        self.assertIsNot(t_shallow_clone._nodes_parent, t._nodes_parent)
        self.assertDefaultDictEqual(t_shallow_clone._nodes_parent, t._nodes_parent)
        self.assertIsNot(t_shallow_clone._nodes_children_list, t._nodes_children_list)
        self.assertDefaultDictEqual(
            t_shallow_clone._nodes_children_list, t._nodes_children_list
        )

        # nodes are shallow copies
        for nid, node in t._nodes_map.items():
            self.assertIs(t_shallow_clone._nodes_map[nid], node)
        tree_sanity_check(t)
        tree_sanity_check(t_shallow_clone)

        # deep = True
        t_custom_deep_clone = t.clone(deep=True)
        for nid, node in t_custom_deep_clone._nodes_map.items():
            self.assertIsNot(t._nodes_map[nid], node)

    def test_clone_with_subtree(self):
        t = get_sample_tree()

        t_clone = t.clone(with_nodes=True, new_root="a")
        tree_sanity_check(t)
        tree_sanity_check(t_clone)
        self.assertIsInstance(t_clone, Tree)
        self.assertIsNot(t_clone, t)
        self.assertFalse(t_clone.is_empty())
        self.assertSetEqual(
            set(t_clone._nodes_map.keys()), {"a", "aa", "ab", "aa0", "aa1"}
        )
        self.assertEqual(
            t_clone.show(),
            """{}
├── a: []
│   ├── AA0
│   └── AA1
└── b: {}
""",
        )
        # nodes are shallow copies
        for _, node in t_clone.list():
            self.assertIs(node, t.get(node.identifier)[1])

    def test_empty_clone(self):
        t = get_sample_tree()

        # deep = False
        t_shallow_empty_clone = t.clone(with_nodes=False)
        self.assertIsInstance(t_shallow_empty_clone, Tree)
        self.assertIsNot(t_shallow_empty_clone, t)
        self.assertTrue(t_shallow_empty_clone.is_empty())
        tree_sanity_check(t)
        tree_sanity_check(t_shallow_empty_clone)

    def test_parent(self):
        t = get_sample_tree()
        with self.assertRaises(NotFoundNodeError):
            t.parent_id("root")
        self.assertEqual(t.parent_id("a"), "root")
        self.assertEqual(t.parent_id("ab"), "a")
        self.assertEqual(t.parent_id("c1"), "c")
        with self.assertRaises(NotFoundNodeError):
            t.parent_id("non-existing-id")

    def test_children(self):
        t = get_sample_tree()
        self.assertEqual(set(t.children_ids("root")), {"a", "c"})
        self.assertEqual(set(t.children_ids("a")), {"aa", "ab"})
        self.assertEqual(t.children_ids("c"), ["c0", "c1"])
        self.assertEqual(set(t.children_ids("aa")), {"aa0", "aa1"})
        self.assertEqual(t.children_ids("c1"), [])
        with self.assertRaises(NotFoundNodeError):
            t.children_ids("non-existing-id")

    def test_siblings(self):
        t = get_sample_tree()
        self.assertEqual(t.siblings_ids("root"), [])
        self.assertEqual(t.siblings_ids("a"), ["c"])
        self.assertEqual(t.siblings_ids("c"), ["a"])
        self.assertEqual(t.siblings_ids("aa0"), ["aa1"])
        self.assertEqual(t.siblings_ids("c1"), ["c0"])
        with self.assertRaises(NotFoundNodeError):
            t.siblings_ids("non-existing-id")

    def test_is_leaf(self):
        t = get_sample_tree()
        self.assertFalse(t.is_leaf("root"))
        self.assertFalse(t.is_leaf("a"))
        self.assertFalse(t.is_leaf("c"))
        self.assertTrue(t.is_leaf("aa0"))
        self.assertTrue(t.is_leaf("aa1"))
        self.assertTrue(t.is_leaf("c1"))
        with self.assertRaises(NotFoundNodeError):
            t.is_leaf("non-existing-id")

    def test_depth(self):
        t = get_sample_tree()
        self.assertEqual(t.depth("root"), 0)
        self.assertEqual(t.depth("a"), 1)
        self.assertEqual(t.depth("c"), 1)
        self.assertEqual(t.depth("aa"), 2)
        self.assertEqual(t.depth("aa0"), 3)
        self.assertEqual(t.depth("ab"), 2)
        self.assertEqual(t.depth("c1"), 2)
        with self.assertRaises(NotFoundNodeError):
            t.depth("non-existing-id")

    def test_ancestors(self):
        t = get_sample_tree()
        self.assertEqual(t.ancestors_ids("root"), [])
        self.assertEqual(t.ancestors_ids("a"), ["root"])
        self.assertEqual(t.ancestors_ids("a", include_current=True), ["a", "root"])
        self.assertEqual(t.ancestors_ids("c"), ["root"])
        self.assertEqual(t.ancestors_ids("c", include_current=True), ["c", "root"])
        self.assertEqual(t.ancestors_ids("aa"), ["a", "root"])
        self.assertEqual(t.ancestors_ids("aa", from_root=True), ["root", "a"])
        self.assertEqual(
            t.ancestors_ids("aa", from_root=True, include_current=True),
            ["root", "a", "aa"],
        )
        self.assertEqual(t.ancestors_ids("ab"), ["a", "root"])
        self.assertEqual(t.ancestors_ids("ab", from_root=True), ["root", "a"])
        self.assertEqual(t.ancestors_ids("c1"), ["c", "root"])
        self.assertEqual(t.ancestors_ids("c1", from_root=True), ["root", "c"])

        with self.assertRaises(NotFoundNodeError):
            t.ancestors("non-existing-id")

    def test_leaves(self):
        t = get_sample_tree()
        self.assertEqual(set(t.leaves_ids()), {"aa0", "aa1", "ab", "c0", "c1"})
        self.assertEqual(set(t.leaves_ids("a")), {"aa0", "aa1", "ab"})
        self.assertEqual(t.leaves_ids("aa0"), ["aa0"])
        self.assertEqual(t.leaves_ids("c"), ["c0", "c1"])

    def test_expand_tree(self):
        t = get_sample_tree()

        # depth mode
        self.assertEqual(
            to_key_id(list(t.expand_tree())),
            [
                (None, "root"),
                ("a", "a"),
                ("a", "aa"),
                (0, "aa0"),
                (1, "aa1"),
                ("b", "ab"),
                ("c", "c"),
                (0, "c0"),
                (1, "c1"),
            ],
        )
        self.assertEqual(
            to_key_id(list(t.expand_tree(reverse=True))),
            [
                (None, "root"),
                ("c", "c"),
                (1, "c1"),
                (0, "c0"),
                ("a", "a"),
                ("b", "ab"),
                ("a", "aa"),
                (1, "aa1"),
                (0, "aa0"),
            ],
        )

        # subtree
        self.assertEqual(
            to_key_id(list(t.expand_tree(nid="a"))),
            [("a", "a"), ("a", "aa"), (0, "aa0"), (1, "aa1"), ("b", "ab")],
        )

        # width mode
        self.assertEqual(
            to_key_id(list(t.expand_tree(mode="width"))),
            [
                (None, "root"),
                ("a", "a"),
                ("c", "c"),
                ("a", "aa"),
                ("b", "ab"),
                (0, "c0"),
                (1, "c1"),
                (0, "aa0"),
                (1, "aa1"),
            ],
        )
        self.assertEqual(
            to_key_id(list(t.expand_tree(mode="width", reverse=True))),
            [
                (None, "root"),
                ("c", "c"),
                ("a", "a"),
                (1, "c1"),
                (0, "c0"),
                ("b", "ab"),
                ("a", "aa"),
                (1, "aa1"),
                (0, "aa0"),
            ],
        )

        # subtree
        self.assertEqual(
            to_key_id(list(t.expand_tree(nid="a", mode="width"))),
            [("a", "a"), ("a", "aa"), ("b", "ab"), (0, "aa0"), (1, "aa1")],
        )

        # filter
        self.assertEqual(
            to_key_id(
                list(t.expand_tree(filter_=lambda k, x: x.identifier in ("root", "c")))
            ),
            [(None, "root"), ("c", "c")],
        )

        # without filter through
        self.assertEqual(
            to_key_id(list(t.expand_tree(filter_=lambda k, x: "1" in x.identifier))), []
        )
        # with filter through
        self.assertEqual(
            to_key_id(
                list(
                    t.expand_tree(
                        filter_=lambda k, x: "1" in x.identifier, filter_through=True
                    )
                )
            ),
            [(1, "aa1"), (1, "c1")],
        )

    def test_iter_nodes_with_location(self):
        t = get_sample_tree()

        def tuple_extend(item, tup):
            return item, tup[0], tup[1]

        # full
        self.assertEqual(
            list(t._iter_nodes_with_location(nid=None, filter_=None, reverse=False)),
            [
                tuple_extend((), t.get("root")),
                tuple_extend((False,), t.get("a")),
                tuple_extend((False, False), t.get("aa")),
                tuple_extend((False, False, False), t.get("aa0")),
                tuple_extend((False, False, True), t.get("aa1")),
                tuple_extend((False, True), t.get("ab")),
                tuple_extend((True,), t.get("c")),
                tuple_extend((True, False), t.get("c0")),
                tuple_extend((True, True), t.get("c1")),
            ],
        )

        # subtree
        self.assertEqual(
            list(t._iter_nodes_with_location(nid="aa", filter_=None, reverse=False)),
            [
                tuple_extend((), t.get("aa")),
                tuple_extend((False,), t.get("aa0")),
                tuple_extend((True,), t.get("aa1")),
            ],
        )

    def test_show(self):
        t = get_sample_tree()
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   ├── a: []
│   │   ├── AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    └── C1
""",
        )

        # limit number of displayed nodes
        self.assertEqual(
            t.show(limit=3),
            """{}
├── a: {}
│   ├── a: []
...
(truncated, total number of nodes: 9)
""",
        )

    def test_prefix_repr(self):
        self.assertEqual(
            Tree._line_prefix_repr(
                line_type="ascii-ex",
                is_last_list=(),
            ),
            "",
        )
        self.assertEqual(
            Tree._line_prefix_repr(line_type="ascii-ex", is_last_list=(True,)), "└── "
        )
        self.assertEqual(
            Tree._line_prefix_repr(line_type="ascii-ex", is_last_list=(False,)), "├── "
        )
        self.assertEqual(
            Tree._line_prefix_repr(
                line_type="ascii-ex", is_last_list=(True, False, True)
            ),
            "    │   └── ",
        )
        self.assertEqual(
            Tree._line_prefix_repr(
                line_type="ascii-ex", is_last_list=(False, False, False)
            ),
            "│   │   ├── ",
        )

    def test_line_repr(self):
        tts = [
            (
                "no key",
                "└──",
                False,
                "start message",
                "end message",
                40,
                "└──start message             end message",
            ),
            (
                "with key",
                "└── a",
                True,
                "start message",
                "end message",
                40,
                "└── a: start message         end message",
            ),
            (
                "no key / too long",
                "└──",
                False,
                "start message",
                "end message",
                15,
                "└──start mes...",
            ),
            (
                "with key / too long",
                "└── a",
                True,
                "start message",
                "end message",
                15,
                "└── a: start...",
            ),
        ]
        for (
            desc,
            prefix,
            is_key_displayed,
            node_start,
            node_end,
            line_max_length,
            expected,
        ) in tts:
            line_repr = Tree._line_repr(
                prefix, is_key_displayed, ": ", node_start, node_end, line_max_length
            )
            self.assertEqual(expected, line_repr, desc)
            self.assertEqual(len(line_repr), line_max_length)

    def test_insert_tree_below(self):
        t = get_sample_tree()

        # insert subtree
        t_to_paste = get_sample_tree_2()
        t.insert(t_to_paste, parent_id="c")
        tree_sanity_check(t)
        tree_sanity_check(t_to_paste)
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   ├── a: []
│   │   ├── AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    ├── C1
    └── []
        ├── {}
        │   └── a: {}
        └── {}
""",
        )
        self.assertTrue(all(nid in t for nid in ("broot", "b1", "b1a", "b2")))
        # by default pasted new tree is a shallow copy
        k, n = t.get("broot")
        self.assertEqual(k, 2)
        k_ini, n_ini = t_to_paste.get("broot")
        self.assertEqual(k_ini, None)
        self.assertEqual(n, n_ini)

        # cannot repaste tree, because then there would be node duplicates
        with self.assertRaises(DuplicatedNodeError):
            t.insert(t_to_paste, parent_id="aa0")
        tree_sanity_check(t)
        tree_sanity_check(t_to_paste)

    def test_insert_tree_at_root(self):
        t = Tree()
        t.insert_tree(get_sample_tree())
        tree_sanity_check(t)
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   ├── a: []
│   │   ├── AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    └── C1
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
            t.insert_tree(get_sample_tree_2(), child_id="aa0")
        self.assertTrue(all(nid not in t for nid in {"broot", "b1", "b1a", "b2"}))
        tree_sanity_check(t)

        # insert subtree with proper specification
        t.insert_tree(
            get_sample_tree_2(), child_id="aa0", child_id_below="b2", key="new-key"
        )
        tree_sanity_check(t)
        self.assertTrue(all(nid in t for nid in {"broot", "b1", "b1a", "b2"}))
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   ├── a: []
│   │   ├── []
│   │   │   ├── {}
│   │   │   │   └── a: {}
│   │   │   └── {}
│   │   │       └── new-key: AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    └── C1
""",
        )

        # insert subtree, without proper child specification, but with only one leaf will by default place children
        # below that leaf
        t = get_sample_tree()
        t2 = get_sample_tree_2()
        t2.drop_node("b2")
        t.insert_tree(t2, child_id="aa0", key="some_key")
        tree_sanity_check(t)
        tree_sanity_check(t2)
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   ├── a: []
│   │   ├── []
│   │   │   └── {}
│   │   │       └── a: {}
│   │   │           └── some_key: AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    └── C1
""",
        )

    def test_merge(self):
        t = get_sample_tree()

        # merge under list
        t_to_merge = get_sample_tree_2()
        t.merge(new_tree=t_to_merge, nid="c")
        tree_sanity_check(t)
        tree_sanity_check(t_to_merge)
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   ├── a: []
│   │   ├── AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── {}
    │   └── a: {}
    ├── {}
    ├── C0
    └── C1
""",
        )
        # new tree root is not conserved
        self.assertTrue("broot" not in t)
        self.assertTrue(all(nid in t for nid in ("b1", "b1a", "b2")))
        old_key, old_node = t_to_merge.get("b1")
        new_key, new_node = t.get("b1")
        self.assertEqual(old_key, new_key)
        self.assertIs(old_node, new_node)

        # cannot remerge tree, because then there would be node duplicates
        with self.assertRaises(DuplicatedNodeError):
            t.merge(new_tree=t_to_merge, nid="aa0")
        tree_sanity_check(t)
        tree_sanity_check(t_to_merge)

        # merge on initial empty tree
        t = Tree()
        t.merge(get_sample_tree_2())
        tree_sanity_check(t)
        self.assertEqual(
            t.show(),
            """[]
├── {}
│   └── a: {}
└── {}
""",
        )
        # in this case new_tree root is conserved since initial tree is empty
        self.assertTrue(all(nid in t for nid in ("broot", "b1", "b1a", "b2")))

    def test_drop_node(self):
        # drop with children
        t = get_sample_tree()
        node_key, aa_node = t.drop_node("aa")
        tree_sanity_check(t)
        self.assertEqual(node_key, "a")
        self.assertIsInstance(aa_node, Node)
        self.assertEqual(aa_node.identifier, "aa")
        self.assertTrue(all(nid not in t for nid in ("aa", "aa0", "aa1")))
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   └── b: {}
└── c: []
    ├── C0
    └── C1
""",
        )

        # drop without children (rebase children to dropped node's parent), possible because node and its parent are of
        # same type
        t2 = get_sample_tree()
        a_key, a_node = t2.drop_node("a", with_children=False)
        tree_sanity_check(t2)
        self.assertEqual(a_key, "a")
        self.assertIsInstance(a_node, Node)
        self.assertTrue(all(nid in t2 for nid in ("aa", "ab", "aa0", "aa1")))
        self.assertTrue("a" not in t2)
        self.assertEqual(
            t2.show(),
            """{}
├── a: []
│   ├── AA0
│   └── AA1
├── b: {}
└── c: []
    ├── C0
    └── C1
""",
        )

        # cannot drop root if it has multiple children
        t3 = get_sample_tree()
        with self.assertRaises(MultipleRootError):
            t3.drop_node("root", with_children=False)

        # drop without children impossible if node type and parent node type are different (because list keys are ints, map keys are str)
        t4 = get_sample_tree()
        with self.assertRaises(ValueError):
            t4.drop_node("aa", with_children=False)

    def test_drop_subtree(self):
        t = get_sample_tree()
        key, a1_subtree = t.drop_subtree("aa")
        self.assertEqual(key, "a")
        self.assertIsInstance(a1_subtree, Tree)
        self.assertEqual(
            sorted(to_key_id(a1_subtree.list()), key=itemgetter(1)),
            sorted([(None, "aa"), (0, "aa0"), (1, "aa1")], key=itemgetter(1)),
        )
        tree_sanity_check(t)
        tree_sanity_check(a1_subtree)
        self.assertEqual(
            sorted(to_key_id(t.list()), key=itemgetter(1)),
            sorted(
                [
                    (None, "root"),
                    ("a", "a"),
                    ("b", "ab"),
                    ("c", "c"),
                    (0, "c0"),
                    (1, "c1"),
                ],
                key=itemgetter(1),
            ),
        )
        self.assertEqual(
            t.show(),
            """{}
├── a: {}
│   └── b: {}
└── c: []
    ├── C0
    └── C1
""",
        )
        self.assertEqual(
            a1_subtree.show(),
            """[]
├── AA0
└── AA1
""",
        )

    def test_get_node_id_by_path(self):
        t = get_sample_tree()
        self.assertEqual(t.get_node_id_by_path("a"), "a")
        self.assertEqual(t.get_node_id_by_path("a.b"), "ab")
        self.assertEqual(t.get_node_id_by_path("a.a.1"), "aa1")
        self.assertEqual(t.get_node_id_by_path("c.1"), "c1")

    def test_subtree(self):
        t = get_sample_tree()

        # by path
        k, st = t.subtree(nid="a.a", by_path=True)
        self.assertEqual(k, "a")
        self.assertEqual(
            st.show(),
            """[]
├── AA0
└── AA1
""",
        )

        # by id
        nid = t.get_node_id_by_path("a.a")
        k, st = t.subtree(nid=nid)
        self.assertEqual(k, "a")
        self.assertEqual(
            st.show(),
            """[]
├── AA0
└── AA1
""",
        )

    def test_path(self):
        t = get_sample_tree()
        for p in ("a.a", "a.b", "a", "", "a.a.1"):
            nid = t.get_node_id_by_path(p)
            self.assertEqual(t.get_path(nid), p)

        t = get_sample_tree(path_separator="|")
        for p in ("a|a", "a|b", "a", "", "a|a|1"):
            nid = t.get_node_id_by_path(p)
            self.assertEqual(t.get_path(nid), p)

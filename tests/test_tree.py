from collections import defaultdict
from operator import itemgetter
import pytest
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


def assert_default_dict_equal(first, second):
    """Assert that two items are defaultdict, and that they have same content, ignoring default values."""
    assert isinstance(first, defaultdict)
    assert isinstance(second, defaultdict)
    assert first.default_factory() == second.default_factory()
    for key in set(first.keys()) | set(second.keys()):
        assert first[key] == second[key]


def test_insert_root():
    t = Tree()
    root_node = Node(identifier="a")
    t.insert_node(root_node)
    assert to_key_id(t.list()) == [(None, "a")]
    t._nodes_map["a"] is root_node
    assert t._nodes_parent["a"] is None
    assert t._nodes_children_list["a"] == []
    assert t._nodes_children_map["a"] == {}
    tree_sanity_check(t)

    # cannot add second root
    with pytest.raises(MultipleRootError):
        t.insert_node(Node(identifier="b"))
    assert to_key_id(t.list()) == [(None, "a")]
    tree_sanity_check(t)

    # wrong node insertion
    with pytest.raises(AttributeError):
        Tree().insert_node({"key": "a"})


def test_insert_node_below():
    t = Tree()
    t.insert_node(Node("root_id"))

    # cannot insert under not existing parent
    with pytest.raises(NotFoundNodeError):
        t.insert_node(Node(identifier="a"), parent_id="what")
    tree_sanity_check(t)

    # insert node below another one
    node_a = Node("a_id")
    t.insert_node(node_a, parent_id="root_id", key="a")
    assert set(t._nodes_map.keys()) == {"root_id", "a_id"}
    assert t._nodes_map["a_id"] == node_a
    assert t._nodes_parent["root_id"] is None
    assert t._nodes_parent["a_id"] == "root_id"
    assert t._nodes_children_list["a_id"] == []
    assert t._nodes_children_map["root_id"] == {"a_id": "a"}
    tree_sanity_check(t)

    # try to insert node with same id than existing node
    with pytest.raises(DuplicatedNodeError):
        t.insert_node(Node("a_id"), parent_id="root_id", key="b")
    tree_sanity_check(t)


def test_insert_node_above():
    # above root
    t = Tree()
    t.insert_node(Node("initial_root"))
    t.insert_node(node=Node("new_root"), child_id="initial_root", key="between")
    assert t.root == "new_root"
    assert to_key_id(t.children("new_root")) == [("between", "initial_root")]
    tree_sanity_check(t)
    assert (
        t.show()
        == """{}
└── between: {}
"""
    )
    # above node
    t = get_sample_tree()
    t.insert_node(Node("new"), child_id="aa0", key="to")
    assert "new" in t
    assert (
        t.show()
        == """{}
├── a: {}
│   ├── a: []
│   │   ├── {}
│   │   │   └── to: AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    └── C1
"""
    )
    tree_sanity_check(t)


def test_validate_node_insertion():
    t = Tree()
    t.insert_node(Node("a"))

    # cannot insert node of wrong class
    class MyNotValidClass(object):
        pass

    with pytest.raises(AttributeError):
        t._validate_node_insertion(MyNotValidClass())
    with pytest.raises(AttributeError):
        t.insert_node({})

    # cannot add node with similar id
    with pytest.raises(DuplicatedNodeError):
        t._validate_node_insertion(Node("a"))


def test_contains():
    t = get_sample_tree()
    assert "aa0" in t
    assert "yolo_id" not in t


def test_get():
    t = get_sample_tree()
    with pytest.raises(NotFoundNodeError):
        t.get("not_existing_id")
    k, n = t.get("ab")
    assert n is t._nodes_map["ab"]
    assert k == "b"

    k, n = t.get("aa1")
    assert n is t._nodes_map["aa1"]
    assert k == 1


def test_list():
    t = get_sample_tree()

    assert to_key_id(t.list(id_in=["a", "c"])) == [("a", "a"), ("c", "c")]
    assert sorted(to_key_id(t.list(depth_in=[0, 2])), key=itemgetter(1)) == sorted(
        [(None, "root"), ("a", "aa"), ("b", "ab"), (0, "c0"), (1, "c1")],
        key=itemgetter(1),
    )
    assert sorted(to_key_id(t.list(depth_in=[3])), key=itemgetter(1)) == sorted(
        [(0, "aa0"), (1, "aa1")], key=itemgetter(1)
    )


def test_is_empty():
    assert Tree().is_empty()
    t = get_sample_tree()
    assert not t.is_empty()


def test_ensure_present():
    t = get_sample_tree()

    # existing node id
    assert t._ensure_present("a", defaults_to_root=False, allow_empty=False) == "a"
    assert t._ensure_present("a", defaults_to_root=True, allow_empty=False) == "a"
    assert t._ensure_present("a", defaults_to_root=False, allow_empty=True) == "a"
    assert t._ensure_present("a", defaults_to_root=True, allow_empty=True) == "a"

    # non-existing node id
    with pytest.raises(NotFoundNodeError):
        t._ensure_present("fake_id", defaults_to_root=False, allow_empty=False)
    with pytest.raises(NotFoundNodeError):
        t._ensure_present("fake_id", defaults_to_root=True, allow_empty=False)
    with pytest.raises(NotFoundNodeError):
        t._ensure_present("fake_id", defaults_to_root=False, allow_empty=True)
    with pytest.raises(NotFoundNodeError):
        t._ensure_present("fake_id", defaults_to_root=True, allow_empty=True)

    # None on non-empty tree
    with pytest.raises(ValueError):
        t._ensure_present(None, defaults_to_root=False, allow_empty=False)
    assert t._ensure_present(None, defaults_to_root=True, allow_empty=False) == "root"
    assert t._ensure_present(None, defaults_to_root=False, allow_empty=True) is None
    assert t._ensure_present(None, defaults_to_root=True, allow_empty=True) == "root"

    # None on empty tree
    empty_tree = Tree()
    with pytest.raises(ValueError):
        empty_tree._ensure_present(None, defaults_to_root=False, allow_empty=False)
    with pytest.raises(ValueError):
        assert (
            empty_tree._ensure_present(None, defaults_to_root=True, allow_empty=False)
            == "root"
        )
    assert (
        empty_tree._ensure_present(None, defaults_to_root=False, allow_empty=True)
        is None
    )
    assert (
        empty_tree._ensure_present(None, defaults_to_root=True, allow_empty=True)
        is None
    )


def test_clone_with_tree():
    t = get_sample_tree()

    # deep = False
    t_shallow_clone = t.clone(with_nodes=True)
    assert isinstance(t_shallow_clone, Tree)
    assert t_shallow_clone is not t
    assert not t_shallow_clone.is_empty()
    assert t_shallow_clone._nodes_map is not t._nodes_map
    assert t_shallow_clone._nodes_map == t._nodes_map
    assert t_shallow_clone._nodes_parent is not t._nodes_parent
    assert_default_dict_equal(t_shallow_clone._nodes_parent, t._nodes_parent)
    assert t_shallow_clone._nodes_children_list is not t._nodes_children_list
    assert_default_dict_equal(
        t_shallow_clone._nodes_children_list, t._nodes_children_list
    )

    # nodes are shallow copies
    for nid, node in t._nodes_map.items():
        assert t_shallow_clone._nodes_map[nid] is node
    tree_sanity_check(t)
    tree_sanity_check(t_shallow_clone)

    # deep = True
    t_custom_deep_clone = t.clone(deep=True)
    for nid, node in t_custom_deep_clone._nodes_map.items():
        assert t._nodes_map[nid] is not node


def test_clone_with_subtree():
    t = get_sample_tree()

    t_clone = t.clone(with_nodes=True, new_root="a")
    tree_sanity_check(t)
    tree_sanity_check(t_clone)
    assert isinstance(t_clone, Tree)
    assert t_clone is not t
    assert not t_clone.is_empty()
    assert set(t_clone._nodes_map.keys()) == {"a", "aa", "ab", "aa0", "aa1"}
    assert (
        t_clone.show()
        == """{}
├── a: []
│   ├── AA0
│   └── AA1
└── b: {}
"""
    )
    # nodes are shallow copies
    for _, node in t_clone.list():
        assert node is t.get(node.identifier)[1]


def test_empty_clone():
    t = get_sample_tree()

    # deep = False
    t_shallow_empty_clone = t.clone(with_nodes=False)
    assert isinstance(t_shallow_empty_clone, Tree)
    assert t_shallow_empty_clone is not t
    assert t_shallow_empty_clone.is_empty()
    tree_sanity_check(t)
    tree_sanity_check(t_shallow_empty_clone)


def test_parent():
    t = get_sample_tree()
    with pytest.raises(NotFoundNodeError):
        t.parent_id("root")
    assert t.parent_id("a") == "root"
    assert t.parent_id("ab") == "a"
    assert t.parent_id("c1") == "c"
    with pytest.raises(NotFoundNodeError):
        t.parent_id("non-existing-id")


def test_children():
    t = get_sample_tree()
    assert set(t.children_ids("root")) == {"a", "c"}
    assert set(t.children_ids("a")) == {"aa", "ab"}
    assert t.children_ids("c") == ["c0", "c1"]
    assert set(t.children_ids("aa")) == {"aa0", "aa1"}
    assert t.children_ids("c1") == []
    with pytest.raises(NotFoundNodeError):
        t.children_ids("non-existing-id")


def test_siblings():
    t = get_sample_tree()
    assert t.siblings_ids("root") == []
    assert t.siblings_ids("a") == ["c"]
    assert t.siblings_ids("c") == ["a"]
    assert t.siblings_ids("aa0") == ["aa1"]
    assert t.siblings_ids("c1") == ["c0"]
    with pytest.raises(NotFoundNodeError):
        t.siblings_ids("non-existing-id")


def test_is_leaf():
    t = get_sample_tree()
    assert not t.is_leaf("root")
    assert not t.is_leaf("a")
    assert not t.is_leaf("c")
    assert t.is_leaf("aa0")
    assert t.is_leaf("aa1")
    assert t.is_leaf("c1")
    with pytest.raises(NotFoundNodeError):
        t.is_leaf("non-existing-id")


def test_depth():
    t = get_sample_tree()
    assert t.depth("root") == 0
    assert t.depth("a") == 1
    assert t.depth("c") == 1
    assert t.depth("aa") == 2
    assert t.depth("aa0") == 3
    assert t.depth("ab") == 2
    assert t.depth("c1") == 2
    with pytest.raises(NotFoundNodeError):
        t.depth("non-existing-id")


def test_ancestors():
    t = get_sample_tree()
    assert t.ancestors_ids("root") == []
    assert t.ancestors_ids("a") == ["root"]
    assert t.ancestors_ids("a", include_current=True) == ["a", "root"]
    assert t.ancestors_ids("c") == ["root"]
    assert t.ancestors_ids("c", include_current=True) == ["c", "root"]
    assert t.ancestors_ids("aa") == ["a", "root"]
    assert t.ancestors_ids("aa", from_root=True) == ["root", "a"]
    assert t.ancestors_ids("aa", from_root=True, include_current=True) == [
        "root",
        "a",
        "aa",
    ]
    assert t.ancestors_ids("ab") == ["a", "root"]
    assert t.ancestors_ids("ab", from_root=True) == ["root", "a"]
    assert t.ancestors_ids("c1") == ["c", "root"]
    assert t.ancestors_ids("c1", from_root=True) == ["root", "c"]

    with pytest.raises(NotFoundNodeError):
        t.ancestors("non-existing-id")


def test_leaves():
    t = get_sample_tree()
    assert set(t.leaves_ids()) == {"aa0", "aa1", "ab", "c0", "c1"}
    assert set(t.leaves_ids("a")) == {"aa0", "aa1", "ab"}
    assert t.leaves_ids("aa0") == ["aa0"]
    assert t.leaves_ids("c") == ["c0", "c1"]


def test_expand_tree():
    t = get_sample_tree()

    # depth mode
    assert to_key_id(list(t.expand_tree())) == [
        (None, "root"),
        ("a", "a"),
        ("a", "aa"),
        (0, "aa0"),
        (1, "aa1"),
        ("b", "ab"),
        ("c", "c"),
        (0, "c0"),
        (1, "c1"),
    ]
    assert to_key_id(list(t.expand_tree(reverse=True))) == [
        (None, "root"),
        ("c", "c"),
        (1, "c1"),
        (0, "c0"),
        ("a", "a"),
        ("b", "ab"),
        ("a", "aa"),
        (1, "aa1"),
        (0, "aa0"),
    ]

    # subtree
    assert to_key_id(list(t.expand_tree(nid="a"))) == [
        ("a", "a"),
        ("a", "aa"),
        (0, "aa0"),
        (1, "aa1"),
        ("b", "ab"),
    ]

    # width mode
    assert to_key_id(list(t.expand_tree(mode="width"))) == [
        (None, "root"),
        ("a", "a"),
        ("c", "c"),
        ("a", "aa"),
        ("b", "ab"),
        (0, "c0"),
        (1, "c1"),
        (0, "aa0"),
        (1, "aa1"),
    ]
    assert to_key_id(list(t.expand_tree(mode="width", reverse=True))) == [
        (None, "root"),
        ("c", "c"),
        ("a", "a"),
        (1, "c1"),
        (0, "c0"),
        ("b", "ab"),
        ("a", "aa"),
        (1, "aa1"),
        (0, "aa0"),
    ]

    # subtree
    assert to_key_id(list(t.expand_tree(nid="a", mode="width"))) == [
        ("a", "a"),
        ("a", "aa"),
        ("b", "ab"),
        (0, "aa0"),
        (1, "aa1"),
    ]

    # filter
    assert to_key_id(
        list(t.expand_tree(filter_=lambda k, x: x.identifier in ("root", "c")))
    ) == [(None, "root"), ("c", "c")]

    # without filter through
    assert (
        to_key_id(list(t.expand_tree(filter_=lambda k, x: "1" in x.identifier))) == []
    )
    # with filter through
    assert to_key_id(
        list(
            t.expand_tree(filter_=lambda k, x: "1" in x.identifier, filter_through=True)
        )
    ) == [(1, "aa1"), (1, "c1")]


def test_iter_nodes_with_location():
    t = get_sample_tree()

    def tuple_extend(item, tup):
        return item, tup[0], tup[1]

    # full
    assert list(t._iter_nodes_with_location(nid=None, filter_=None, reverse=False)) == [
        tuple_extend((), t.get("root")),
        tuple_extend((False,), t.get("a")),
        tuple_extend((False, False), t.get("aa")),
        tuple_extend((False, False, False), t.get("aa0")),
        tuple_extend((False, False, True), t.get("aa1")),
        tuple_extend((False, True), t.get("ab")),
        tuple_extend((True,), t.get("c")),
        tuple_extend((True, False), t.get("c0")),
        tuple_extend((True, True), t.get("c1")),
    ]

    # subtree
    assert list(t._iter_nodes_with_location(nid="aa", filter_=None, reverse=False)) == [
        tuple_extend((), t.get("aa")),
        tuple_extend((False,), t.get("aa0")),
        tuple_extend((True,), t.get("aa1")),
    ]


def test_show():
    t = get_sample_tree()
    assert (
        t.show()
        == """{}
├── a: {}
│   ├── a: []
│   │   ├── AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    └── C1
"""
    )

    # limit number of displayed nodes
    assert (
        t.show(limit=3)
        == """{}
├── a: {}
│   ├── a: []
...
(truncated, total number of nodes: 9)
"""
    )


def test_prefix_repr():
    assert (
        Tree._line_prefix_repr(
            line_type="ascii-ex",
            is_last_list=(),
        )
        == ""
    )
    assert Tree._line_prefix_repr(line_type="ascii-ex", is_last_list=(True,)) == "└── "
    assert Tree._line_prefix_repr(line_type="ascii-ex", is_last_list=(False,)) == "├── "

    assert (
        Tree._line_prefix_repr(line_type="ascii-ex", is_last_list=(True, False, True))
        == "    │   └── "
    )
    assert (
        Tree._line_prefix_repr(line_type="ascii-ex", is_last_list=(False, False, False))
        == "│   │   ├── "
    )


def test_line_repr():
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
        assert expected == line_repr
        assert len(line_repr) == line_max_length


def test_insert_tree_below():
    t = get_sample_tree()

    # insert subtree
    t_to_paste = get_sample_tree_2()
    t.insert(t_to_paste, parent_id="c")
    tree_sanity_check(t)
    tree_sanity_check(t_to_paste)
    assert (
        t.show()
        == """{}
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
"""
    )
    assert all(nid in t for nid in ("broot", "b1", "b1a", "b2"))
    # by default pasted new tree is a shallow copy
    k, n = t.get("broot")
    assert k == 2
    k_ini, n_ini = t_to_paste.get("broot")
    assert k_ini is None
    assert n == n_ini

    # cannot repaste tree, because then there would be node duplicates
    with pytest.raises(DuplicatedNodeError):
        t.insert(t_to_paste, parent_id="aa0")
    tree_sanity_check(t)
    tree_sanity_check(t_to_paste)


def test_insert_tree_at_root():
    t = Tree()
    t.insert_tree(get_sample_tree())
    tree_sanity_check(t)
    assert (
        t.show()
        == """{}
├── a: {}
│   ├── a: []
│   │   ├── AA0
│   │   └── AA1
│   └── b: {}
└── c: []
    ├── C0
    └── C1
"""
    )

    # cannot insert at root if already present root
    t = Tree()
    t.insert_node(Node("present_root"))
    with pytest.raises(MultipleRootError):
        t.insert_tree(get_sample_tree())
    tree_sanity_check(t)


def test_insert_tree_above():
    t = get_sample_tree()

    # cannot insert subtree above if inserted tree has multiple leaves, and without specifying under which new tree
    # node existing children should be placed
    with pytest.raises(ValueError):
        t.insert_tree(get_sample_tree_2(), child_id="aa0")
    assert all(nid not in t for nid in {"broot", "b1", "b1a", "b2"})
    tree_sanity_check(t)

    # insert subtree with proper specification
    t.insert_tree(
        get_sample_tree_2(), child_id="aa0", child_id_below="b2", key="new-key"
    )
    tree_sanity_check(t)
    assert all(nid in t for nid in {"broot", "b1", "b1a", "b2"})
    assert (
        t.show()
        == """{}
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
"""
    )

    # insert subtree, without proper child specification, but with only one leaf will by default place children
    # below that leaf
    t = get_sample_tree()
    t2 = get_sample_tree_2()
    t2.drop_node("b2")
    t.insert_tree(t2, child_id="aa0", key="some_key")
    tree_sanity_check(t)
    tree_sanity_check(t2)
    assert (
        t.show()
        == """{}
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
"""
    )


def test_merge():
    t = get_sample_tree()

    # merge under list
    t_to_merge = get_sample_tree_2()
    t.merge(new_tree=t_to_merge, nid="c")
    tree_sanity_check(t)
    tree_sanity_check(t_to_merge)
    assert (
        t.show()
        == """{}
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
"""
    )
    # new tree root is not conserved
    assert "broot" not in t
    assert all(nid in t for nid in ("b1", "b1a", "b2"))
    old_key, old_node = t_to_merge.get("b1")
    new_key, new_node = t.get("b1")
    assert old_key == new_key
    assert old_node is new_node

    # cannot remerge tree, because then there would be node duplicates
    with pytest.raises(DuplicatedNodeError):
        t.merge(new_tree=t_to_merge, nid="aa0")
    tree_sanity_check(t)
    tree_sanity_check(t_to_merge)

    # merge on initial empty tree
    t = Tree()
    t.merge(get_sample_tree_2())
    tree_sanity_check(t)
    assert (
        t.show()
        == """[]
├── {}
│   └── a: {}
└── {}
"""
    )
    # in this case new_tree root is conserved since initial tree is empty
    assert all(nid in t for nid in ("broot", "b1", "b1a", "b2"))


def test_drop_node():
    # drop with children
    t = get_sample_tree()
    node_key, aa_node = t.drop_node("aa")
    tree_sanity_check(t)
    assert node_key == "a"
    assert isinstance(aa_node, Node)
    assert aa_node.identifier == "aa"
    assert all(nid not in t for nid in ("aa", "aa0", "aa1"))
    assert (
        t.show()
        == """{}
├── a: {}
│   └── b: {}
└── c: []
    ├── C0
    └── C1
"""
    )

    # drop without children (rebase children to dropped node's parent), possible because node and its parent are of
    # same type
    t2 = get_sample_tree()
    a_key, a_node = t2.drop_node("a", with_children=False)
    tree_sanity_check(t2)
    assert a_key == "a"
    assert isinstance(a_node, Node)
    assert all(nid in t2 for nid in ("aa", "ab", "aa0", "aa1"))
    assert "a" not in t2
    assert (
        t2.show()
        == """{}
├── a: []
│   ├── AA0
│   └── AA1
├── b: {}
└── c: []
    ├── C0
    └── C1
"""
    )

    # cannot drop root if it has multiple children
    t3 = get_sample_tree()
    with pytest.raises(MultipleRootError):
        t3.drop_node("root", with_children=False)

    # drop without children impossible if node type and parent node type are different (because list keys are ints, map keys are str)
    t4 = get_sample_tree()
    with pytest.raises(ValueError):
        t4.drop_node("aa", with_children=False)


def test_drop_subtree():
    t = get_sample_tree()
    key, a1_subtree = t.drop_subtree("aa")
    assert key == "a"
    assert isinstance(a1_subtree, Tree)
    assert sorted(to_key_id(a1_subtree.list()), key=itemgetter(1)) == sorted(
        [(None, "aa"), (0, "aa0"), (1, "aa1")], key=itemgetter(1)
    )
    tree_sanity_check(t)
    tree_sanity_check(a1_subtree)
    assert sorted(to_key_id(t.list()), key=itemgetter(1)) == sorted(
        [
            (None, "root"),
            ("a", "a"),
            ("b", "ab"),
            ("c", "c"),
            (0, "c0"),
            (1, "c1"),
        ],
        key=itemgetter(1),
    )
    assert (
        t.show()
        == """{}
├── a: {}
│   └── b: {}
└── c: []
    ├── C0
    └── C1
"""
    )
    assert (
        a1_subtree.show()
        == """[]
├── AA0
└── AA1
"""
    )


def test_get_node_id_by_path():
    t = get_sample_tree()
    assert t.get_node_id_by_path(["a"]) == "a"
    assert t.get_node_id_by_path(["a", "b"]) == "ab"
    assert t.get_node_id_by_path(["a", "a", 1]) == "aa1"
    assert t.get_node_id_by_path(["c", 1]) == "c1"


def test_subtree():
    t = get_sample_tree()

    # by id
    nid = t.get_node_id_by_path(["a", "a"])
    k, st = t.subtree(nid=nid)
    assert k == "a"
    assert (
        st.show()
        == """[]
├── AA0
└── AA1
"""
    )


def test_path():
    t = get_sample_tree()
    for p in [["a", "a"], ["a", "b"], ["a"], [], ["a", "a", 1]]:
        nid = t.get_node_id_by_path(p)
        assert t.get_path(nid) == p

    # strict = False -> coerce "1" -> int
    t = get_sample_tree()
    nid = t.get_node_id_by_path(["a", "a", "1"])
    assert t.get_path(nid) == ["a", "a", 1]

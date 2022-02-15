from lighttree.implementations.json_tree import (
    JsonTree,
    InteractiveJson,
    as_interactive_json,
)


def test_json_tree():
    j = JsonTree({"a": [{}, {"b": 12}, [1, 2, 3]]})
    assert (
        j.__str__()
        == """{}
└── a: []
    ├── {}
    ├── {}
    │   └── b: 12
    └── []
        ├── 1
        ├── 2
        └── 3
"""
    )


def test_as_interactive_json_tree():
    j = as_interactive_json({"a": [{}, {"b": 12}, [1, 2, 3]]})
    assert (
        j.__str__()
        == """<InteractiveJson>
{}
└── a: []
    ├── {}
    ├── {}
    │   └── b: 12
    └── []
        ├── 1
        ├── 2
        └── 3
"""
    )
    assert "a" in dir(j)
    a = j.a
    assert isinstance(a, InteractiveJson)
    as_json = a()
    assert as_json == [{}, {"b": 12}, [1, 2, 3]]

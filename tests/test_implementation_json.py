from unittest import TestCase

from lighttree.implementations.json_tree import (
    JsonTree,
    InteractiveJson,
    as_interactive_json,
)


class JSONTestCase(TestCase):
    def test_json_tree(self):
        j = JsonTree({"a": [{}, {"b": 12}, [1, 2, 3]]})
        self.assertEqual(
            j.__str__(),
            """{}
└── a: []
    ├── {}
    ├── {}
    │   └── b: 12
    └── []
        ├── 1
        ├── 2
        └── 3
""",
        )

    def test_as_interactive_json_tree(self):
        j = as_interactive_json({"a": [{}, {"b": 12}, [1, 2, 3]]})
        self.assertEqual(
            j.__str__(),
            """<InteractiveJson>
{}
└── a: []
    ├── {}
    ├── {}
    │   └── b: 12
    └── []
        ├── 1
        ├── 2
        └── 3
""",
        )
        self.assertIn("a", dir(j))
        a = j.a
        self.assertIsInstance(a, InteractiveJson)
        as_json = a()
        self.assertEqual(as_json, [{}, {"b": 12}, [1, 2, 3]])

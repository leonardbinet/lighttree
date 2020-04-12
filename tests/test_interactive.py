#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import sys

from unittest import TestCase

from lighttree import TreeBasedObj
from lighttree.interactive import Obj, is_valid_attr_name, _coerce_attr
from tests.testing_utils import get_sample_custom_tree


class ObjTestCase(TestCase):
    def test_is_valid_attr_name(self):
        self.assertFalse(is_valid_attr_name("__"))
        self.assertFalse(is_valid_attr_name("__salut"))
        self.assertFalse(is_valid_attr_name(".salut"))
        self.assertFalse(is_valid_attr_name("@salut"))
        self.assertFalse(is_valid_attr_name("2salut"))

        self.assertTrue(is_valid_attr_name("_salut"))
        self.assertTrue(is_valid_attr_name("salut_2"))
        self.assertTrue(is_valid_attr_name("_2_salut"))

    def test_coerce_attr(self):
        self.assertEqual(_coerce_attr("_salut"), "_salut")
        self.assertEqual(_coerce_attr(".salut"), "_salut")
        self.assertEqual(_coerce_attr("2salut"), "_2salut")
        self.assertEqual(_coerce_attr("salut$"), "salut_")
        self.assertEqual(_coerce_attr("salut-2022"), "salut_2022")

        self.assertEqual(_coerce_attr("__salut"), None)
        self.assertEqual(_coerce_attr("_"), None)
        self.assertEqual(_coerce_attr("--"), None)

    def test_set_obj_attribute(self):
        obj = Obj()

        # valid key
        # set by __setitem__
        obj["some_key"] = "some_value"
        self.assertEqual(obj.some_key, "some_value")
        self.assertEqual(obj["some_key"], "some_value")
        self.assertIn("some_key", dir(obj))

        # set by __setattr__
        obj.some_key_2 = "some_value_2"
        self.assertEqual(obj.some_key_2, "some_value_2")
        self.assertEqual(obj["some_key_2"], "some_value_2")
        self.assertIn("some_key_2", dir(obj))

        # key containing '-' character can not be set as attribute
        obj["some-key"] = "some-value"
        self.assertEqual(obj["some-key"], "some-value")
        # internally stored in mangled '__d' attribute -> '_Obj__d'
        self.assertIn("some-key", obj["_Obj__d"])
        self.assertEqual(obj["_Obj__d"]["some-key"], "some-value")

        self.assertEqual(obj.__str__(), "<Obj> ['some-key', 'some_key', 'some_key_2']")

        # key beginning with figure cannot be set as attribute
        obj["2-some-key"] = "some-value"
        self.assertEqual(obj["2-some-key"], "some-value")
        self.assertNotIn("2-some-key", dir(obj))

    def test_obj_attr_set_with_coercion(self):
        class ObjWithAttrCoercion(Obj):
            _COERCE_ATTR = True

        obj = ObjWithAttrCoercion()
        obj[".some_key"] = "some_value"
        self.assertEqual(obj._some_key, "some_value")
        self.assertEqual(obj[".some_key"], "some_value")
        self.assertIn("_some_key", dir(obj))

    def test_obj_init(self):
        t = "type" if sys.version_info[0] == 2 else "class"

        obj = Obj(yolo="yolo value", toto="toto value")
        self.assertEqual(obj.yolo, "yolo value")
        self.assertEqual(obj.toto, "toto value")

        # with underscores
        obj2 = Obj(_yolo="yolo value", _toto="toto value")
        self.assertEqual(obj2._yolo, "yolo value")
        self.assertEqual(obj2._toto, "toto value")

        # unauthorized attributes/keys
        with self.assertRaises(ValueError) as e:
            Obj(__d="trying to mess around")
        self.assertEqual(
            e.exception.args[0],
            "Attribute <__d> of type <<%s 'str'>> is not valid." % t,
        )

        with self.assertRaises(ValueError) as e:
            obj = Obj()
            obj[23] = "yolo"
        self.assertEqual(
            e.exception.args[0],
            "Key <23> of type <<%s 'int'>> cannot be set as attribute on <Obj> instance."
            % t,
        )
        with self.assertRaises(ValueError) as e:
            obj = Obj()
            obj[None] = "yolo"
        self.assertEqual(
            e.exception.args[0],
            "Key <None> of type <<%s 'NoneType'>> cannot be set as attribute on <Obj> instance."
            % t,
        )

        # if other that string is accepted
        class FlexObj(Obj):
            _STRING_KEY_CONSTRAINT = False

        # unauthorized attributes/keys
        with self.assertRaises(ValueError) as e:
            FlexObj(__d="trying to mess around")
        self.assertEqual(
            e.exception.args[0],
            "Attribute <__d> of type <<%s 'str'>> is not valid." % t,
        )

        # authorized:
        obj = FlexObj()
        obj[23] = "yolo"
        self.assertEqual(obj[23], "yolo")

        obj = FlexObj()
        obj[None] = "yolo"
        self.assertEqual(obj[None], "yolo")

    def test_obj_inherit(self):
        class MyCustomObj(Obj):
            pass

        obj = MyCustomObj()

        obj["some-key"] = "some-value"
        self.assertEqual(obj["some-key"], "some-value")
        # still stored in mangled '__d' attribute of initial Obj class -> '_Obj__d'
        self.assertIn("some-key", obj["_Obj__d"])
        self.assertEqual(obj["_Obj__d"]["some-key"], "some-value")

        self.assertEqual(obj.__str__(), "<MyCustomObj> ['some-key']")

        class MyOtherCustomObj(Obj):
            _REPR_NAME = "CallMe"

        other_obj = MyOtherCustomObj(maybe="...")
        self.assertEqual(other_obj.__str__(), "<CallMe> ['maybe']")


class TreeBasedObjTestCase(TestCase):
    def test_tree_based_obj(self):
        """Check expand and shallow copy.
        - check that an object expand its tree's chilren in its attributes
        - check that no deep copy is made when expanding trees. More precisely, since we might manipulate
        lots of nodes, we want to check that nodes are never copied. Instead their reference is passed to different
        trees.
        """

        class InteractiveTree(TreeBasedObj):
            _REPR_NAME = "SomeCoolTree"
            _NODE_PATH_ATTR = "identifier"

        # if None depth is passed, the tree does not expand
        no_expand_obj = InteractiveTree(tree=get_sample_custom_tree(), depth=None)
        for child in ("a", "b"):
            self.assertFalse(hasattr(no_expand_obj, child))

        # if depth is passed, the tree expand
        obj = InteractiveTree(tree=get_sample_custom_tree(), depth=1)
        for child in ("a", "b"):
            self.assertTrue(hasattr(obj, child))

        # when accessing child, check that it auto-expands children
        obj.a.a1
        a = obj.a
        """
        a
        ├── a1
        │   ├── a11
        │   └── a12
        └── a2
        """
        self.assertTrue(hasattr(a, "a1"))
        # check that initial tree, and child tree reference the same nodes
        self.assertIs(a._tree.get("a1"), obj._tree.get("a1"))

        # test representations
        self.assertEqual(
            obj.__str__(),
            """<SomeCoolTree>
root
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
            a.__str__(),
            """<SomeCoolTree subpart: a>
a
├── a1
│   ├── a11
│   └── a12
└── a2
""",
        )
        self.assertEqual(
            a.a1.__str__(),
            """<SomeCoolTree subpart: a.a1>
a1
├── a11
└── a12
""",
        )

    def test_tree_set_get_attrs(self):
        obj = TreeBasedObj(tree=get_sample_custom_tree())
        obj["some_key"] = "some_value"
        self.assertEqual(obj.some_key, "some_value")
        self.assertEqual(obj["some_key"], "some_value")
        self.assertIn("some_key", dir(obj))

        # set by __setattr__
        obj.some_key_2 = "some_value_2"
        self.assertEqual(obj.some_key_2, "some_value_2")
        self.assertEqual(obj["some_key_2"], "some_value_2")
        self.assertIn("some_key_2", dir(obj))

        # key containing '-' character can not be set as attribute
        obj["some-key"] = "some-value"
        self.assertEqual(obj["some-key"], "some-value")
        # internally stored in mangled '__d' attribute -> '_Obj__d'
        self.assertIn("some-key", obj["_Obj__d"])
        self.assertEqual(obj["_Obj__d"]["some-key"], "some-value")

        # key beginning with figure cannot be set as attribute
        obj["2-some-key"] = "some-value"
        self.assertEqual(obj["2-some-key"], "some-value")
        self.assertNotIn("2-some-key", dir(obj))

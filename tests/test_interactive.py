import sys
import pytest

from lighttree import TreeBasedObj
from lighttree.interactive import Obj, is_valid_attr_name, _coerce_attr
from .testing_utils import get_sample_tree


def test_is_valid_attr_name():
    assert not is_valid_attr_name("__")
    assert not is_valid_attr_name("__salut")
    assert not is_valid_attr_name(".salut")
    assert not is_valid_attr_name("@salut")
    assert not is_valid_attr_name("2salut")

    assert is_valid_attr_name("_salut")
    assert is_valid_attr_name("salut_2")
    assert is_valid_attr_name("_2_salut")


def test_coerce_attr():
    assert _coerce_attr("_salut") == "_salut"
    assert _coerce_attr(".salut") == "_salut"
    assert _coerce_attr("2salut") == "_2salut"
    assert _coerce_attr("salut$") == "salut_"
    assert _coerce_attr("salut-2022") == "salut_2022"
    assert _coerce_attr("__salut") is None
    assert _coerce_attr("_") is None
    assert _coerce_attr("--") is None


def test_set_obj_attribute():
    obj = Obj()

    # valid key
    # set by __setitem__
    obj["some_key"] = "some_value"
    assert obj.some_key == "some_value"
    assert obj["some_key"] == "some_value"
    assert "some_key" in dir(obj)

    # set by __setattr__
    obj.some_key_2 = "some_value_2"
    assert obj.some_key_2 == "some_value_2"
    assert obj["some_key_2"] == "some_value_2"
    assert "some_key_2" in dir(obj)

    # key containing '-' character can not be set as attribute
    obj["some-key"] = "some-value"
    assert obj["some-key"] == "some-value"
    # internally stored in mangled '__d' attribute -> '_Obj__d'
    assert "some-key" in obj["_Obj__d"]
    assert obj["_Obj__d"]["some-key"] == "some-value"

    assert obj.__str__() == "<Obj> ['some-key', 'some_key', 'some_key_2']"

    # key beginning with figure cannot be set as attribute
    obj["2-some-key"] = "some-value"
    assert obj["2-some-key"] == "some-value"
    assert "2-some-key" not in dir(obj)


def test_obj_attr_set_with_coercion():
    class ObjWithAttrCoercion(Obj):
        _COERCE_ATTR = True

    obj = ObjWithAttrCoercion()
    obj[".some_key"] = "some_value"
    assert obj._some_key == "some_value"
    assert obj[".some_key"] == "some_value"
    assert "_some_key" in dir(obj)


def test_obj_init():
    t = "type" if sys.version_info[0] == 2 else "class"

    obj = Obj(yolo="yolo value", toto="toto value")
    assert obj.yolo == "yolo value"
    assert obj.toto == "toto value"

    # with underscores
    obj2 = Obj(_yolo="yolo value", _toto="toto value")
    assert obj2._yolo == "yolo value"
    assert obj2._toto == "toto value"

    # unauthorized attributes/keys
    with pytest.raises(ValueError) as e:
        Obj(__d="trying to mess around")
    assert e.value.args[0] == "Attribute <__d> of type <<%s 'str'>> is not valid." % t

    with pytest.raises(ValueError) as e:
        obj = Obj()
        obj[23] = "yolo"
    assert (
        e.value.args[0]
        == "Key <23> of type <<%s 'int'>> cannot be set as attribute on <Obj> instance."
        % t
    )
    with pytest.raises(ValueError) as e:
        obj = Obj()
        obj[None] = "yolo"
    assert (
        e.value.args[0]
        == "Key <None> of type <<%s 'NoneType'>> cannot be set as attribute on <Obj> instance."
        % t
    )

    # if other that string is accepted
    class FlexObj(Obj):
        _STRING_KEY_CONSTRAINT = False

    # unauthorized attributes/keys
    with pytest.raises(ValueError) as e:
        FlexObj(__d="trying to mess around")
    assert e.value.args[0] == "Attribute <__d> of type <<%s 'str'>> is not valid." % t

    # authorized:
    obj = FlexObj()
    obj[23] = "yolo"
    assert obj[23] == "yolo"

    obj = FlexObj()
    obj[None] = "yolo"
    assert obj[None] == "yolo"


def test_obj_inherit():
    class MyCustomObj(Obj):
        pass

    obj = MyCustomObj()

    obj["some-key"] = "some-value"
    assert obj["some-key"] == "some-value"
    # still stored in mangled '__d' attribute of initial Obj class -> '_Obj__d'
    assert "some-key" in obj["_Obj__d"]
    assert obj["_Obj__d"]["some-key"] == "some-value"
    assert obj.__str__() == "<MyCustomObj> ['some-key']"

    class MyOtherCustomObj(Obj):
        _REPR_NAME = "CallMe"

    other_obj = MyOtherCustomObj(maybe="...")
    assert other_obj.__str__() == "<CallMe> ['maybe']"


def test_tree_based_obj():
    """Check expand and shallow copy.
    - check that an object expand its tree's children in its attributes
    - check that no deep copy is made when expanding trees. More precisely, since we might manipulate
    lots of nodes, we want to check that nodes are never copied. Instead their reference is passed to different
    trees.
    """

    class InteractiveTree(TreeBasedObj):
        _REPR_NAME = "SomeCoolTree"

    # if None depth is passed, the tree does not expand
    no_expand_obj = InteractiveTree(tree=get_sample_tree(), depth=None)
    for child in ("a", "b"):
        assert not (hasattr(no_expand_obj, child))

    # if depth is passed, the tree expand
    obj = InteractiveTree(tree=get_sample_tree(), depth=1)
    for child in ("a", "c"):
        assert hasattr(obj, child)

    # when accessing child, check that it auto-expands children
    obj.a.a.i0
    a = obj.a
    """
    _ {}
    ├── a {}
    │   ├── aa []
    │   │   ├── aa0
    │   │   └── aa1
    │   └── ab {}
    └── c []
        ├── c0
        └── c1
    """
    assert hasattr(a, "a")
    assert a._tree.get("aa") == obj._tree.get("aa")

    # test representations
    assert (
        obj._show()
        == """<SomeCoolTree>
{}
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
    assert (
        a._show()
        == """<SomeCoolTree subpart: a>
{}
├── a: []
│   ├── AA0
│   └── AA1
└── b: {}
"""
    )
    assert (
        a.a.i0._show()
        == """<SomeCoolTree subpart: a.a.0>
AA0
"""
    )


def test_tree_set_get_attrs():
    obj = TreeBasedObj(tree=get_sample_tree())
    obj["some_key"] = "some_value"
    assert obj.some_key == "some_value"
    assert obj["some_key"] == "some_value"
    assert "some_key" in dir(obj)

    # set by __setattr__
    obj.some_key_2 = "some_value_2"
    assert obj.some_key_2 == "some_value_2"
    assert obj["some_key_2"] == "some_value_2"
    assert "some_key_2" in dir(obj)

    # key containing '-' character can not be set as attribute
    obj["some-key"] = "some-value"
    assert obj["some-key"] == "some-value"
    # internally stored in mangled '__d' attribute -> '_Obj__d'
    assert "some-key" in obj["_Obj__d"]
    assert obj["_Obj__d"]["some-key"] == "some-value"

    # key beginning with figure cannot be set as attribute
    obj["2-some-key"] = "some-value"
    assert obj["2-some-key"] == "some-value"
    assert "2-some-key" not in dir(obj)

from typing import Dict, Optional, Any, Union, List
from lighttree import Tree, Key, AutoIdNode
from lighttree.node import NodeId
from lighttree.interactive import TreeBasedObj


class JsonTree(Tree):
    def __init__(
        self, d: Optional[Dict] = None, strict: bool = True, path_separator: str = "."
    ) -> None:
        """
        :param d:
        :param strict: if False, will convert tuples into arrays, else raise error
        :param path_separator: separator used to build path
        """
        super(JsonTree, self).__init__(path_separator=path_separator)
        if d is not None:
            self._fill(d, strict=strict, key=None)

    @staticmethod
    def _concat(a: Any, b: Any) -> str:
        if not a and not b:
            return ""
        if not a:
            return str(b)
        return ".".join([str(a), str(b)])

    def _fill(self, data: Any, key: Key, strict: bool, path: str = "") -> None:
        pid: Optional[NodeId]
        if self.is_empty():
            pid = None
        else:
            pid = self.get_node_id_by_path(path=path)
        if isinstance(data, list) or not strict and isinstance(data, tuple):
            k = self.insert_node(AutoIdNode(keyed=False), parent_id=pid, key=key)
            path = self._concat(path, k)
            for el in data:
                self._fill(el, strict=strict, path=path, key=None)
            return
        if isinstance(data, dict):
            k = self.insert_node(AutoIdNode(keyed=True), key=key, parent_id=pid)
            path = self._concat(path, k)
            for sk, el in data.items():
                self._fill(el, strict=strict, path=path, key=sk)
            return
        if isinstance(data, (str, int, float)):
            self.insert_node(
                AutoIdNode(accept_children=False, repr_=str(data), data=data),
                parent_id=pid,
                key=key,
            )
            return
        if data is None:
            self.insert_node(AutoIdNode(accept_children=False), parent_id=pid)
            return
        raise TypeError("Unsupported type %s" % type(data))

    def to_json(self) -> Union[Dict, List, None]:
        if self.root is None:
            return None
        return self._to_json(self.root)

    def _to_json(self, nid: NodeId) -> Any:
        _, n = self.get(nid)
        if not n.accept_children:
            return n.data
        if n.keyed:
            d = {}
            for sk, sn in self.children(n.identifier):
                d[sk] = self._to_json(sn.identifier)
            return d
        l_ = []
        for _, sn in self.children(n.identifier):
            l_.append(self._to_json(sn.identifier))
        return l_


class InteractiveJson(TreeBasedObj):

    _tree: JsonTree

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._tree.to_json()


def as_interactive_json(d: Any, strict: bool = False) -> InteractiveJson:
    return InteractiveJson(tree=JsonTree(d, strict=strict))

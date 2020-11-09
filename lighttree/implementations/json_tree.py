from six import text_type
from lighttree import Node, Tree


class JsonTree(Tree):
    def __init__(self, d=None, strict=True, path_separator="."):
        """
        :param d:
        :param strict: if False, will convert tuples into arrays, else raise error
        :param path_separator: separator used to build path
        """
        super(JsonTree, self).__init__(path_separator=path_separator)
        if d is not None:
            self._fill(d, strict=strict, key=None)

    @staticmethod
    def _concat(a, b):
        if not a and not b:
            return ""
        if not a:
            return str(b)
        return ".".join([str(a), str(b)])

    def _fill(self, data, key, strict, path=None):
        if isinstance(data, list) or not strict and isinstance(data, tuple):
            k = self.insert_node(
                Node(keyed=False), parent_id=path, key=key, by_path=True
            )
            path = self._concat(path, k)
            for el in data:
                self._fill(el, strict=strict, path=path, key=None)
            return
        if isinstance(data, dict):
            k = self.insert_node(
                Node(keyed=True), key=key, parent_id=path, by_path=True
            )
            path = self._concat(path, k)
            for sk, el in data.items():
                self._fill(el, strict=strict, path=path, key=sk)
            return
        if isinstance(data, (text_type, int, float)):
            self.insert_node(
                Node(accept_children=False, repr_=data, data=data),
                parent_id=path,
                key=key,
                by_path=True,
            )
            return
        if data is None:
            self.insert_node(Node(accept_children=False), parent_id=path, by_path=True)
            return
        raise TypeError("Unsupported type %s" % type(data))

    def to_dict(self):
        return self._to_dict(self.root)

    def _to_dict(self, nid):
        _, n = self.get(nid)
        if not n.accept_children:
            return n.data
        if n.keyed:
            d = {}
            for sk, sn in self.children(n.identifier):
                d[sk] = self._to_dict(sn.identifier)
            return d
        d = []
        for _, sn in self.children(n.identifier):
            d.append(self._to_dict(sn.identifier))
        return d

import uuid
from typing import Optional, Any, Tuple
from dataclasses import dataclass

NodeId = str


@dataclass
class Node:

    identifier: NodeId
    keyed: bool = True
    accept_children: bool = True
    repr_: Optional[str] = None
    data: Any = None

    def line_repr(self, depth: int, **kwargs: Any) -> Tuple[str, str]:
        """Control how node is displayed in tree representation.
        First returned string is how node is represented on left, second string is how node is represented on right.

        MyTree
        ├── one                                        OneEnd
        │   └── two                                    twoEnd
        └── three                                    threeEnd
        """
        if self.repr_ is not None:
            return self.repr_, ""
        if not self.accept_children:
            if hasattr(self.data, "__str__"):
                return str(self.data), ""
            return "", ""
        if self.keyed:
            return "{}", ""
        return "[]", ""


class AutoIdNode(Node):
    def __init__(
        self,
        identifier: Optional[NodeId] = None,
        keyed: bool = True,
        accept_children: bool = True,
        repr_: Optional[str] = None,
        data: Any = None,
    ):

        self._auto_generated_id: bool
        identifier_: NodeId

        if identifier is None:
            identifier_ = str(uuid.uuid4())
            self._auto_generated_id = True
        else:
            identifier_ = identifier
            self._auto_generated_id = False

        super(AutoIdNode, self).__init__(
            identifier=identifier_,
            keyed=keyed,
            accept_children=accept_children,
            repr_=repr_,
            data=data,
        )

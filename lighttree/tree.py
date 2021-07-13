#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy

from typing import (
    Tuple,
    Union,
    Optional,
    List,
    Sequence,
    Callable,
    Iterable,
    cast,
    Dict,
    Any,
)
from collections import defaultdict
from operator import itemgetter

from lighttree.node import Node
from .exceptions import MultipleRootError, NotFoundNodeError, DuplicatedNodeError
from .utils import STYLES


Key = Union[None, str, int]
KeyedNode = Tuple[Key, Node]
KeyedTree = Tuple[Key, "Tree"]


class Tree(object):

    """Principles:
    - each node is identified by an id
    - a tree cannot contain multiple nodes with same id
    - there are 2 types of nodes:
        - "map" nodes under which children nodes are referenced by a key (keyed=True)
        - "list" nodes under which children nodes are referenced by order (keyed=False)
    - node referencing in tree is done by defining under which node it should be placed and under which key/order

    For performance reasons, child id <-> parent id is store both ways:
    - parent id -> children ids
    - children id -> parent id

    """

    def __init__(self, path_separator: str = ".") -> None:
        self.path_separator = path_separator

        # nodes references and hierarchy in tree
        self.root: Optional[str] = None
        # node identifier -> node
        self._nodes_map: Dict[str, Node] = {}
        # node identifier -> parent node identifier
        self._nodes_parent: Dict[str, Optional[str]] = defaultdict(lambda: None)
        # "map" node identifier -> map of children nodes identifier -> key
        self._nodes_children_map: Dict[str, Dict[str, Union[int, str]]] = defaultdict(
            dict
        )
        # "list" node identifier -> children nodes identifiers
        self._nodes_children_list: Dict[str, List[str]] = defaultdict(list)

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._nodes_map

    def get(self, nid: str, by_path: bool = False) -> KeyedNode:
        """Get a node by its id.
        :param nid: str, identifier of node to fetch
        :param by_path: bool, if True nid is the path to the node
        :rtype: lighttree.node.Node
        """
        if by_path:
            nid = self.get_node_id_by_path(nid)
        self._ensure_present(nid)
        return self.get_key(nid), self._nodes_map[nid]

    def child_id(self, nid: str, key: Union[str, int], by_path: bool = False) -> str:
        _, node = self.get(nid, by_path=by_path)
        if node.keyed:
            child_id = next(
                (cid for cid, k in self._nodes_children_map[nid].items() if k == key),
                None,
            )
            if child_id is None:
                raise ValueError("No child of key %s below %s" % (key, nid))
            return child_id
        try:
            int(key)
        except (ValueError, TypeError):
            raise ValueError("Expected integer key, got %s" % key)
        return self._nodes_children_list[nid][int(key)]

    def child(self, nid: str, key: Union[int, str], by_path: bool = False) -> KeyedNode:
        return self.get(self.child_id(nid, key, by_path=by_path))

    def get_node_id_by_path(self, path: str) -> str:
        nid = self.root
        if nid is None:
            raise ValueError("Empty tree")
        if path == "":
            return nid
        keys = str(path).split(self.path_separator)
        for k in keys:
            nid = self.child_id(nid, k)
        if nid is None:
            raise ValueError("Empty tree")
        return nid

    def get_path(self, nid: str) -> str:
        return self.path_separator.join(
            [
                str(k)
                for k, _ in self.ancestors(nid, from_root=True, include_current=True)[
                    1:
                ]
            ]
        )

    def get_key(self, nid: str) -> Key:
        """Get a node's key.
        :param nid: str, identifier of node

        If root: -> return None
        If parent node is a map: return key
        If parent node is a list: return index
        """
        self._ensure_present(nid)
        if nid == self.root:
            return None
        _, parent_node = self.parent(nid)
        if parent_node.keyed:
            return self._nodes_children_map[parent_node.identifier][nid]
        return self._nodes_children_list[parent_node.identifier].index(nid)

    def list(
        self,
        id_in: Optional[Sequence[str]] = None,
        depth_in: Optional[Sequence[int]] = None,
        filter_: Optional[Callable[[Node], bool]] = None,
    ) -> List[KeyedNode]:
        """List nodes.
        :param id_in: list of str, optional, filter nodes among provided identifiers
        :param depth_in: list of int, optional, filter nodes whose depth in tree is among provided values
        :param filter\_: function, optional, filtering function to apply to each node
        :rtype: list of lighttree.node.Node
        """
        return [
            (self.get_key(nid), node)
            for nid, node in self._nodes_map.items()
            if (id_in is None or nid in id_in)
            and (filter_ is None or filter_(node))
            and (depth_in is None or self.depth(nid) in depth_in)
        ]

    def is_empty(self) -> bool:
        """Return whether tree is empty (contains nodes) or not.
        :rtype: bool
        """
        return self.root is None

    def _ensure_present(
        self,
        nid: Optional[str],
        defaults_to_root: bool = False,
        allow_empty: bool = False,
    ) -> Union[None, str]:
        if nid is None:
            if not self.is_empty() and defaults_to_root:
                return self.root
            if allow_empty:
                return None
            raise ValueError("'nid' set to None not supported.")
        if nid not in self:
            raise NotFoundNodeError("Node id <%s> doesn't exist in tree" % nid)
        return nid

    def _validate_node_insertion(self, node: Node) -> None:
        if node.identifier in self._nodes_map.keys():
            raise DuplicatedNodeError(
                "Can't create node with id '%s'" % node.identifier
            )

    def _validate_tree_insertion(self, tree: "Tree") -> None:
        for node_key, node in tree.list():
            # todo validate key
            self._validate_node_insertion(node)

    def _clone_init(self, deep: bool) -> "Tree":
        """Method intended to be overloaded, to avoid rewriting whole methods relying on `clone` method when
        inheriting from Tree, so that the way a tree is duplicated is explicit.

        >>> class TreeWithComposition(Tree):
        >>>     def __init__(self, tree_description, large_data):
        >>>         super(TreeWithComposition, self).__init__()
        >>>         self.tree_description = tree_description
        >>>         self.large_data = large_data
        >>>
        >>>     def _clone_init(self, deep=False):
        >>>         return TreeWithComposition(
        >>>             tree_description=self.tree_description,
        >>>             large_data=copy.deepcopy(self.large_data) if deep else self.large_data
        >>>         )
        >>>
        >>> my_custom_tree = TreeWithComposition(tree_description="smart tree")
        >>> subtree = my_custom_tree.subtree()
        >>> subtree.tree_description
        "smart tree"

        :param: deep, boolean, in case of composition should its potential elements be deep copied or not.
        """
        return self.__class__()

    def clone(
        self, with_nodes: bool = True, deep: bool = False, new_root: str = None
    ) -> "Tree":
        """Clone current instance, with or without nodes.
        :rtype: :class:`lighttree.tree.Tree`
        """
        new_tree = self._clone_init(deep)
        if not with_nodes:
            return new_tree

        # remove eventual created nodes at init
        if new_tree.root:
            new_tree.drop_node(new_tree.root)
        for i, (key, node) in enumerate(self.expand_tree(nid=new_root)):
            nid = node.identifier
            if deep:
                node = copy.deepcopy(node)
            if i == 0:
                # necessary in case of new_root (the new root has no parent nor key)
                pid = None
                key = None
            else:
                pid = self.parent_id(nid)
            new_tree.insert_node(node, parent_id=pid, key=key)
        return new_tree

    def parent(self, nid: str) -> KeyedNode:
        """Return parent node.
        Return None if given node id is root.
        """
        pid = self.parent_id(nid)
        if pid is None:
            raise NotFoundNodeError("Node <%s> has no parent" % nid)
        return self.get(pid)

    def parent_id(self, nid: str, by_path: bool = False) -> str:
        if nid == self.root:
            raise NotFoundNodeError("Root node has not parent")
        if by_path:
            nid = self.get_node_id_by_path(nid)
        self._ensure_present(nid)
        parent_id = self._nodes_parent[nid]
        if parent_id is None:
            # cannot happen, only for typing
            raise NotFoundNodeError()
        return parent_id

    def children(self, nid: str, by_path: bool = False) -> List[KeyedNode]:
        """Return set of given node children node ids."""
        return [self.get(id_) for id_ in self.children_ids(nid, by_path=by_path)]

    def children_ids(self, nid: str, by_path: bool = False) -> List[str]:
        if self.get(nid, by_path=by_path)[1].keyed:
            return list(self._nodes_children_map[nid].keys())
        return list(self._nodes_children_list[nid])

    def siblings(self, nid: str, by_path: bool = False) -> List[KeyedNode]:
        """Return set of ids of nodes that share the provided node's parent."""
        return [self.get(id_) for id_ in self.siblings_ids(nid, by_path=by_path)]

    def siblings_ids(self, nid: str, by_path: bool = False) -> List[str]:
        if by_path:
            nid = self.get_node_id_by_path(nid)
        self._ensure_present(nid)
        if nid == self.root:
            return []
        parent_id = self.parent_id(nid)
        if parent_id is None:
            return []
        return list(set(self.children_ids(parent_id)).difference({nid}))

    def is_leaf(self, nid: str, by_path: bool = False) -> bool:
        """Return is node is a leaf in this tree."""
        return len(self.children_ids(nid, by_path=by_path)) == 0

    def depth(self, nid: str, by_path: bool = False) -> int:
        """Return node depth, 0 means root."""
        return len(self.ancestors_ids(nid, by_path=by_path))

    def ancestors(
        self,
        nid: str,
        from_root: bool = False,
        include_current: bool = False,
        by_path: bool = False,
    ) -> List[KeyedNode]:
        """From element to root.
        :param nid:
        :param from_root:
        :param include_current:
        :param by_path:
        :return:
        """
        return [
            self.get(id_)
            for id_ in self.ancestors_ids(
                nid, from_root, include_current, by_path=by_path
            )
        ]

    def ancestors_ids(
        self,
        nid: str,
        from_root: bool = False,
        include_current: bool = False,
        by_path: bool = False,
    ) -> List[str]:
        if by_path:
            nid = self.get_node_id_by_path(nid)
        self._ensure_present(nid)
        ancestor_ids = [nid] if include_current else []
        if nid == self.root:
            return ancestor_ids
        while nid != self.root:
            nid = self.parent_id(nid)
            ancestor_ids.append(nid)
        if from_root:
            ancestor_ids = list(reversed(ancestor_ids))
        return ancestor_ids

    def subtree(self, nid: str, deep: bool = False, by_path: bool = False) -> KeyedTree:
        if by_path:
            nid = self.get_node_id_by_path(nid)
        t = self.clone(with_nodes=True, new_root=nid, deep=deep)
        if t.root is None:
            return None, t
        return self.get_key(t.root), t

    def leaves(
        self, nid: Optional[str] = None, by_path: bool = False
    ) -> List[KeyedNode]:
        """Return leaves under a node subtree."""
        return [self.get(id_) for id_ in self.leaves_ids(nid, by_path=by_path)]

    def leaves_ids(self, nid: Optional[str] = None, by_path: bool = False) -> List[str]:
        tree = self if nid is None else self.subtree(nid, by_path=by_path)[1]
        return [id_ for id_ in tree._nodes_map.keys() if tree.is_leaf(id_)]

    def insert(
        self,
        item: Union[Node, "Tree"],
        parent_id: Optional[str] = None,
        child_id: Optional[str] = None,
        child_id_below: Optional[str] = None,
        key: Optional[Union[int, str]] = None,
        by_path: bool = False,
    ) -> "Tree":
        if isinstance(item, Node):
            if child_id_below is not None:
                raise ValueError(
                    '"child_id_below" parameter is reserved to Tree insertion.'
                )
            self.insert_node(
                node=item,
                parent_id=parent_id,
                child_id=child_id,
                key=key,
                by_path=by_path,
            )
            return self
        if isinstance(item, Tree):
            self.insert_tree(
                new_tree=item,
                parent_id=parent_id,
                child_id=child_id,
                child_id_below=child_id_below,
                key=key,
                by_path=by_path,
            )
            return self
        raise ValueError(
            '"item" parameter must either be a Node, or a Tree, got <%s>.' % type(item)
        )

    def insert_node(
        self,
        node: Node,
        parent_id: Optional[str] = None,
        child_id: Optional[str] = None,
        key: Optional[Union[int, str]] = None,
        by_path: bool = False,
    ) -> Key:
        """Insert node, return key
        :param node:
        :param parent_id:
        :param child_id:
        :param key:
        :return:
        """
        self._validate_node_insertion(node)
        if parent_id is not None and child_id is not None:
            raise ValueError('Can declare at most "parent_id" or "child_id"')
        if child_id is not None:
            self._insert_node_above(node, child_id=child_id, key=key, by_path=by_path)
            return None
        self._insert_node_below(node, parent_id=parent_id, key=key, by_path=by_path)
        return self.get_key(node.identifier)

    def _insert_node_below(
        self,
        node: Node,
        parent_id: Optional[str],
        key: Union[None, int, str],
        by_path: bool,
    ) -> None:
        # insertion at root
        if parent_id is None:
            if not self.is_empty():
                raise MultipleRootError("A tree takes one root merely.")
            if key is not None:
                raise ValueError("No key on root node")
            self.root = node.identifier
            self._nodes_map[node.identifier] = node
            return

        if by_path:
            parent_id = self.get_node_id_by_path(path=parent_id)
        self._ensure_present(parent_id)
        node_id = node.identifier

        _, parent = self.get(parent_id)
        if not parent.accept_children:
            raise ValueError("Parent node %s does not accept children." % parent_id)

        # map
        if parent.keyed:
            if key is None:
                raise ValueError("Key is compulsory")
            if not isinstance(key, str):
                raise ValueError('Key must be of type "str", got %s' % type(key))
            if key in self._nodes_children_map[parent_id]:
                # TODO add overwrite parameter
                raise KeyError(
                    "Already present node for key %s under %s node." % (key, parent_id)
                )
            self._nodes_map[node_id] = node
            self._nodes_parent[node_id] = parent_id
            self._nodes_children_map[parent_id][node_id] = key
            return

        # list
        if key is None:
            self._nodes_children_list[parent_id].append(node_id)
        else:
            if not isinstance(key, int):
                raise ValueError("Key must be of type int, got %s" % type(key))
            self._nodes_children_list[parent_id].insert(key, node_id)
        self._nodes_map[node_id] = node
        self._nodes_parent[node_id] = parent_id

    def _insert_node_above(
        self, node: Node, child_id: str, key: Union[None, int, str], by_path: bool
    ) -> None:
        if by_path:
            child_id = self.get_node_id_by_path(path=child_id)
        self._ensure_present(child_id)
        # get parent_id before dropping subtree
        try:
            parent_id = self.parent_id(nid=child_id)
            has_parent = True
        except NotFoundNodeError:
            parent_id = "fake-for-typing"
            has_parent = False
        subtree_key, child_subtree = self.drop_subtree(nid=child_id)
        if has_parent:
            self._insert_node_below(
                node=node, parent_id=parent_id, key=subtree_key, by_path=False
            )
        else:
            self._insert_node_below(
                node=node, parent_id=None, key=subtree_key, by_path=False
            )
        self._insert_tree_below(
            new_tree=child_subtree, parent_id=node.identifier, key=key, by_path=False
        )

    def insert_tree(
        self,
        new_tree: "Tree",
        parent_id: Optional[str] = None,
        child_id: Optional[str] = None,
        child_id_below: Optional[str] = None,
        key: Optional[Union[str, int]] = None,
        by_path: bool = False,
    ) -> Key:
        """Return new key"""
        self._validate_tree_insertion(new_tree)
        if new_tree.root is None:
            raise ValueError("Empty inserted tree")
        if parent_id is not None and child_id is not None:
            raise ValueError('Can declare at most "parent_id" or "child_id"')
        if child_id is not None:
            self._insert_tree_above(
                new_tree=new_tree,
                child_id=child_id,
                child_id_below=child_id_below,
                key=key,
                by_path=by_path,
            )
        else:
            self._insert_tree_below(
                new_tree, parent_id=parent_id, key=key, by_path=by_path
            )
        if new_tree.root is None:
            # not possible, but for typing
            raise ValueError("Empty inserted tree")
        return self.get_key(new_tree.root)

    def _insert_tree_below(
        self,
        new_tree: "Tree",
        parent_id: Optional[str],
        key: Union[None, str, int],
        by_path: bool,
    ) -> "Tree":
        if parent_id is None:
            # insertion at root requires tree to be empty
            if not self.is_empty():
                raise MultipleRootError("A tree takes one root merely.")
        else:
            if by_path:
                parent_id = self.get_node_id_by_path(parent_id)
            self._ensure_present(parent_id)
        self._validate_tree_insertion(new_tree)

        if new_tree.is_empty():
            return self

        for i, (new_key, new_node) in enumerate(new_tree.expand_tree()):
            if i == 0:
                new_key = key
            nid = new_node.identifier
            pid = parent_id if nid == new_tree.root else new_tree.parent_id(nid)
            self.insert_node(new_node, parent_id=pid, key=new_key)
        return self

    def _insert_tree_above(
        self,
        new_tree: "Tree",
        child_id: str,
        child_id_below: Optional[str],
        key: Union[None, str, int],
        by_path: bool,
    ) -> None:
        # make all checks before modifying tree
        if by_path:
            child_id = self.get_node_id_by_path(child_id)
        self._ensure_present(child_id)
        if child_id_below is not None:
            if by_path:
                child_id_below = self.get_node_id_by_path(child_id_below)
            new_tree._ensure_present(child_id_below)
        else:
            new_tree_leaves = new_tree.leaves_ids()
            if len(new_tree_leaves) > 1:
                raise ValueError(
                    'Ambiguous tree insertion, use "child_id_below" to specify under which node of new'
                    "tree you want to place existing nodes."
                )
            # by default take leaf if unique
            child_id_below = new_tree_leaves.pop()
        parent_id = self.parent_id(child_id)
        subtree_key, child_subtree = self.drop_subtree(child_id)
        self._insert_tree_below(new_tree, parent_id, key=subtree_key, by_path=False)
        self._insert_tree_below(child_subtree, child_id_below, key=key, by_path=False)

    def _drop_node(self, nid: str) -> KeyedNode:
        """Return key, node"""
        if self.children_ids(nid):
            raise ValueError("Cannot drop node having children.")
        key, node = self.get(nid)
        if nid != self.root:
            # dereference parent from child
            _, parent_node = self.parent(nid)
            pid = parent_node.identifier
            self._nodes_parent.pop(nid)
            # dereference child from parent
            if parent_node.keyed:
                self._nodes_children_map[pid].pop(nid)
            else:
                self._nodes_children_list[pid].remove(nid)
        # remove all references to node children (checked that empty before-hand)
        if node.keyed:
            self._nodes_children_map.pop(nid)
        else:
            self._nodes_children_list.pop(nid)
        self._nodes_map.pop(nid)
        # dereference root if needed
        if nid == self.root:
            self.root = None
        return key, node

    def drop_node(
        self,
        nid: str,
        with_children: bool = True,
        by_path: bool = False,
    ) -> KeyedNode:
        """If with_children is False, children of this node will take as new parent the dropped node parent.
        Possible only if node type is same as parent node type.

        Return key, node.
        """
        if by_path:
            nid = self.get_node_id_by_path(nid)
        self._ensure_present(nid)

        children_ids = self.children_ids(nid)
        if with_children:
            for cid in children_ids:
                self.drop_node(nid=cid, with_children=True)
            return self._drop_node(nid=nid)

        # drop a single node, and re-attach children to parent
        removed_key, removed_subtree = self.subtree(nid)
        if nid == self.root and len(children_ids) > 1:
            raise MultipleRootError(
                "Cannot drop current root <%s> without its children, else tree would have "
                "multiple roots" % nid
            )
        _, parent = self.parent(nid)
        _, node = self.get(nid)
        if parent.keyed != node.keyed:
            raise ValueError("Invalid operation.")
        pid = parent.identifier
        self.drop_node(nid, with_children=True)
        for cid in children_ids:
            k, st = removed_subtree.subtree(cid)
            self._insert_tree_below(new_tree=st, parent_id=pid, key=k, by_path=False)
        return removed_key, node

    def drop_subtree(self, nid: str, by_path: bool = False) -> KeyedTree:
        if by_path:
            nid = self.get_node_id_by_path(nid)
        self._ensure_present(nid)
        key, removed_subtree = self.subtree(nid)
        self.drop_node(nid=nid, with_children=True)
        return key, removed_subtree

    def expand_tree(
        self,
        nid: Optional[str] = None,
        by_path: bool = False,
        mode: str = "depth",
        filter_: Optional[Callable[[Union[None, str, int], Node], bool]] = None,
        filter_through: bool = False,
        reverse: bool = False,
    ) -> Iterable[KeyedNode]:
        """Python generator traversing the tree (or a subtree) with optional node filtering.

        Inspired by treelib implementation https://github.com/caesar0301/treelib/blob/master/treelib/tree.py#L374

        :param nid: Node identifier from which tree traversal will start. If None tree root will be used
        :param mode: Traversal mode, may be either "depth" or "width"
        :param filter_: filter function performed on nodes. Node excluded from filter function won't be yielded.
        :param filter_through: if True, excluded nodes don't exclude their children.
        :param reverse: the ``reverse`` param for sorting :class:`Node` objects in the same level
        :return: node ids that satisfy the conditions if ``id_only`` is True, else nodes.
        :rtype: generator
        """
        if mode not in ("depth", "width"):
            raise NotImplementedError("Traversal mode '%s' is not supported" % mode)
        if nid is not None and by_path:
            nid = self.get_node_id_by_path(nid)
        nid = self._ensure_present(nid, defaults_to_root=True, allow_empty=True)
        if nid is not None:
            key, node = self.get(nid)
            filter_pass_node = filter_ is None or filter_(key, node)
            if filter_pass_node:
                yield key, node
            if filter_pass_node or filter_through:
                queue = [
                    (child_key, child_node)
                    for child_key, child_node in self.children(nid)
                    if filter_ is None
                    or filter_through
                    or filter_(child_key, child_node)
                ]
                queue.sort(key=itemgetter(0), reverse=reverse)
                while queue:
                    current_key, current_node = queue.pop(0)
                    if filter_ is None or filter_(current_key, current_node):
                        yield current_key, current_node
                    expansion = [
                        (gchild_key, gchild_node)
                        for gchild_key, gchild_node in self.children(
                            current_node.identifier
                        )
                        if filter_ is None
                        or filter_through
                        or filter_(gchild_key, gchild_node)
                    ]
                    expansion.sort(key=itemgetter(0), reverse=reverse)
                    if mode == "depth":
                        queue = expansion + queue  # depth-first
                    elif mode == "width":
                        queue = queue + expansion  # width-first

    def show(
        self,
        nid: Optional[str] = None,
        by_path: bool = False,
        filter_: Optional[Callable[[Node], bool]] = None,
        display_key: bool = True,
        reverse: bool = False,
        line_type: str = "ascii-ex",
        limit: Optional[int] = None,
        line_max_length: int = 60,
        key_delimiter: str = ": ",
        **kwargs: Any
    ) -> str:
        """Return tree structure in hierarchy style.

        :param nid: Node identifier from which tree traversal will start. If None tree root will be used
        :param filter\_: filter function performed on nodes. Nodes excluded from filter function nor their children won't be displayed
        :param reverse: the ``reverse`` param for sorting :class:`Node` objects in the same level
        :param display_key: boolean, if True display keyed nodes keys
        :param reverse: reverse parameter applied at sorting
        :param line_type: display type choice
        :param limit: int, truncate tree display to this number of lines
        :param kwargs: kwargs params passed to node ``line_repr`` method
        :param line_max_length
        :rtype: unicode in python2, str in python3

        """
        output = ""
        if nid is not None and by_path:
            nid = self.get_node_id_by_path(nid)

        for is_last_list, key, node in self._iter_nodes_with_location(
            nid, filter_, reverse
        ):
            prefix = self._line_prefix_repr(line_type, is_last_list)
            # do not display nb in list in case of non-keyed children (int key)
            if isinstance(key, str) and display_key:
                prefix += key
            node_start, node_end = node.line_repr(
                depth=len(is_last_list), prefix_len=len(prefix), **kwargs
            )

            line = self._line_repr(
                prefix=prefix,
                is_key_displayed=isinstance(key, str) and display_key,
                key_delimiter=key_delimiter,
                node_start=node_start,
                node_end=node_end,
                line_max_length=line_max_length,
            )

            output += "%s\n" % line
            if limit is not None:
                limit -= 1
                if limit == 0:
                    output += "...\n(truncated, total number of nodes: %d)\n" % (
                        len(self._nodes_map.keys())
                    )
                    return output
        return output

    def _iter_nodes_with_location(
        self,
        nid: Optional[str],
        filter_: Optional[Callable[[Node], bool]],
        reverse: bool,
        is_last_list: Optional[List[bool]] = None,
    ) -> Iterable[Tuple[Tuple[bool, ...], Key, Node]]:
        """Yield nodes with information on how they are placed.
        :param nid: starting node identifier
        :param filter_: filter function applied on nodes
        :param reverse: reverse parameter applied at sorting
        :param is_last_list: list of booleans, each indicating if node is the last yielded one at this depth
        :return: tuple of booleans, node
        """
        is_last_list = is_last_list or []

        nid = self._ensure_present(nid, defaults_to_root=True, allow_empty=True)
        if nid is not None:
            key, node = self.get(nid)
            if filter_ is None or filter_(node):
                yield tuple(is_last_list), key, node
                children = [
                    (child_key, child_node)
                    for child_key, child_node in self.children(nid)
                    if filter_ is None or filter_(child_node)
                ]
                idxlast: int = len(children) - 1
                children.sort(key=itemgetter(0), reverse=reverse)
                for idx, (child_k, child) in enumerate(children):
                    is_last_list.append(idx == idxlast)
                    for item in self._iter_nodes_with_location(
                        nid=child.identifier,
                        filter_=filter_,
                        reverse=reverse,
                        is_last_list=is_last_list,
                    ):
                        yield item
                    is_last_list.pop()

    @staticmethod
    def _line_repr(
        prefix: str,
        is_key_displayed: bool,
        key_delimiter: str,
        node_start: str,
        node_end: str,
        line_max_length: int,
    ) -> str:
        line: str = prefix
        if node_start and is_key_displayed:
            line += key_delimiter
        line += node_start
        if node_end:
            padding = max(line_max_length - len(line) - len(node_end), 0)
            line += padding * " " + node_end
        if len(line) > line_max_length:
            line = line[: line_max_length - 3] + "..."
        return line

    @staticmethod
    def _line_prefix_repr(line_type: str, is_last_list: Tuple[bool, ...]) -> str:
        if not is_last_list:
            return ""
        dt_vertical_line, dt_line_box, dt_line_corner = STYLES[line_type]
        leading: str = "".join(
            [
                dt_vertical_line + " " * 3 if not is_last else " " * 4
                for is_last in cast(Iterable[bool], is_last_list[0:-1])
            ]
        )
        lasting: str = dt_line_corner if is_last_list[-1] else dt_line_box
        return leading + lasting

    def merge(
        self, new_tree: "Tree", nid: Optional[str] = None, by_path: bool = False
    ) -> "Tree":
        """Merge "new_tree" on current tree by pasting its root children on current tree "nid" node.

        Consider the following trees:

        >>> self.show()
        root
        ├── A
        └── B
        >>> new_tree.show()
        root2
        ├── C
        └── D
            └── D1

        Merging new_tree on B node:

        >>> self.merge(new_tree, 'B')
        >>> self.show()
        root
        ├── A
        └── B
            ├── C
            └── D
                └── D1

        Note: if current tree is empty and nid is None, the new_tree root will be used as root on current tree. In all
        other cases new_tree root is not pasted.

        """
        if nid is not None and by_path:
            nid = self.get_node_id_by_path(nid)

        if not isinstance(new_tree, self.__class__):
            raise ValueError(
                'Wrong type of "new_tree", expected <%s>, got <%s>'
                % (self.__class__.__name__, new_tree.__class__.__name__)
            )

        if self.is_empty():
            return self.insert(new_tree, parent_id=None, by_path=False)

        nid = self._ensure_present(nid, defaults_to_root=True)

        if new_tree.root is None:
            # not possible, only for typing
            raise ValueError("Inserted tree is empty")
        for ckey, cnode in new_tree.children(new_tree.root):
            self.insert(new_tree.subtree(cnode.identifier)[1], nid, key=ckey)
        return self

    def __str__(self) -> str:
        return self.show()

    def __repr__(self) -> str:
        return self.__str__()

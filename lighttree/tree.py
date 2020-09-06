#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import copy

from future.utils import python_2_unicode_compatible, iteritems, string_types

from collections import defaultdict
from operator import attrgetter, itemgetter

from lighttree.node import Node
from .utils import STYLES
from .exceptions import MultipleRootError, NotFoundNodeError, DuplicatedNodeError


@python_2_unicode_compatible
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

    def __init__(self):
        # nodes references and hierarchy in tree
        self.root = None
        # node identifier -> node
        self._nodes_map = {}
        # node identifier -> parent node identifier
        self._nodes_parent = defaultdict(lambda: None)
        # "map" node identifier -> map of children nodes identifier -> key
        self._nodes_children_map = defaultdict(dict)
        # "list" node identifier -> children nodes identifiers
        self._nodes_children_list = defaultdict(list)

    def __contains__(self, identifier):
        return identifier in self._nodes_map

    def get(self, nid):
        """Get a node by its id.
        :param nid: str, identifier of node to fetch
        :rtype: lighttree.node.Node
        """
        self._ensure_present(nid)
        return self.get_key(nid), self._nodes_map[nid]

    def get_key(self, nid):
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

    def list(self, id_in=None, depth_in=None, filter_=None):
        """List nodes.
        :param id_in: list of str, optional, filter nodes among provided identifiers
        :param depth_in: list of int, optional, filter nodes whose depth in tree is among provided values
        :param filter\_: function, optional, filtering function to apply to each node
        :rtype: list of lighttree.node.Node
        """
        return [
            (self.get_key(nid), node)
            for nid, node in iteritems(self._nodes_map)
            if (id_in is None or nid in id_in)
            and (filter_ is None or filter_(node))
            and (depth_in is None or self.depth(nid) in depth_in)
        ]

    def is_empty(self):
        """Return whether tree is empty (contains nodes) or not.
        :rtype: bool
        """
        return self.root is None

    def _ensure_present(self, nid, defaults_to_root=False, allow_empty=False):
        if nid is None:
            if not self.is_empty() and defaults_to_root:
                return self.root
            if allow_empty:
                return None
            raise ValueError("'nid' set to None not supported.")
        if nid not in self:
            raise NotFoundNodeError("Node id <%s> doesn't exist in tree" % nid)
        return nid

    def _validate_node_insertion(self, node):
        if not isinstance(node, Node):
            raise ValueError("Node must be instance of <Node>, got <%s>." % type(node))
        if node.identifier in self._nodes_map.keys():
            raise DuplicatedNodeError(
                "Can't create node with id '%s'" % node.identifier
            )

    def _validate_tree_insertion(self, tree):
        if not isinstance(tree, Tree):
            raise ValueError(
                "Tree must be instance of <%s>, got <%s>"
                % (self.__class__.__name__, type(tree))
            )
        for node_key, node in tree.list():
            # todo validate key
            self._validate_node_insertion(node)

    def _clone_init(self, deep):
        """Method intended to be overloaded, to avoid rewriting whole methods relying on `clone` method when
        inheriting from Tree, so that the way a tree is duplicated is explicit.

        >>> class TreeWithComposition(Tree):
        >>>     def __init__(self, tree_description):
        >>>         super(TreeWithComposition, self).__init__()
        >>>         self.tree_description = tree_description
        >>>
        >>>     def _clone_init(self, deep=False):
        >>>         return TreeWithComposition(
        >>>             tree_description=deepcopy(self.tree_description) if deep else self.tree_description
        >>>         )
        >>>
        >>> my_custom_tree = TreeWithComposition(tree_description="smart tree")
        >>> subtree = my_custom_tree.subtree()
        >>> subtree.tree_description
        "smart tree"

        :param: deep, boolean, in case of composition should its potential elements be deep copied or not.
        """
        return self.__class__()

    def clone(self, with_nodes=True, deep=False, new_root=None):
        """Clone current instance, with or without nodes.
        :rtype: :class:`lighttree.tree.Tree`
        """
        new_tree = self._clone_init(deep)
        if not with_nodes:
            return new_tree

        for i, (key, node) in enumerate(self.expand_tree(nid=new_root)):
            nid = node.identifier
            if deep:
                node = copy.deepcopy(node)
            if i == 0:
                pid = None
                key = None
            else:
                pid = self.parent_id(nid)
            new_tree.insert_node(node, parent_id=pid, key=key)
        return new_tree

    def parent(self, nid):
        """Return parent node.
        Return None if given node id is root.
        """
        pid = self.parent_id(nid)
        if pid is None:
            return None, None
        return self.get(pid)

    def parent_id(self, nid):
        self._ensure_present(nid)
        if nid == self.root:
            return None
        return self._nodes_parent[nid]

    def children(self, nid):
        """Return set of given node children node ids."""
        return [self.get(id_) for id_ in self.children_ids(nid)]

    def children_ids(self, nid):
        if self.get(nid)[1].keyed:
            return list(self._nodes_children_map[nid].keys())
        return list(self._nodes_children_list[nid])

    def siblings(self, nid):
        """Return set of ids of nodes that share the provided node's parent."""
        return [self.get(id_) for id_ in self.siblings_ids(nid)]

    def siblings_ids(self, nid):
        self._ensure_present(nid)
        if nid == self.root:
            return []
        return list(set(self.children_ids(self.parent_id(nid))).difference({nid}))

    def is_leaf(self, nid):
        """Return is node is a leaf in this tree."""
        return len(self.children_ids(nid)) == 0

    def depth(self, nid):
        """Return node depth, 0 means root."""
        return len(self.ancestors_ids(nid))

    def ancestors(self, nid, from_root=False, include_current=False):
        return [
            self.get(id_) for id_ in self.ancestors_ids(nid, from_root, include_current)
        ]

    def ancestors_ids(self, nid, from_root=False, include_current=False):
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

    def subtree(self, nid, deep=False):
        t = self.clone(with_nodes=True, new_root=nid, deep=deep)
        if t.is_empty():
            return None, t
        return self.get_key(t.root), t

    def leaves(self, nid=None):
        """Return leaves under a node subtree."""
        return [self.get(id_) for id_ in self.leaves_ids(nid)]

    def leaves_ids(self, nid=None):
        tree = self if nid is None else self.subtree(nid)[1]
        return [id_ for id_ in tree._nodes_map.keys() if tree.is_leaf(id_)]

    def insert(
        self, item, parent_id=None, child_id=None, child_id_below=None, key=None
    ):
        if isinstance(item, Node):
            if child_id_below is not None:
                raise ValueError(
                    '"child_id_below" parameter is reserved to Tree insertion.'
                )
            self.insert_node(node=item, parent_id=parent_id, child_id=child_id, key=key)
            return self
        if isinstance(item, Tree):
            self.insert_tree(
                new_tree=item,
                parent_id=parent_id,
                child_id=child_id,
                child_id_below=child_id_below,
                key=key,
            )
            return self
        raise ValueError(
            '"item" parameter must either be a Node, or a Tree, got <%s>.' % type(item)
        )

    def insert_node(self, node, parent_id=None, child_id=None, key=None):
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
            self._insert_node_above(node, child_id=child_id, key=key)
            return self
        self._insert_node_below(node, parent_id=parent_id, key=key)
        return self.get_key(node.identifier)

    def _insert_node_below(self, node, parent_id, key):
        # insertion at root
        if parent_id is None:
            if not self.is_empty():
                raise MultipleRootError("A tree takes one root merely.")
            if key is not None:
                raise ValueError("No key on root node")
            self.root = node.identifier
            self._nodes_map[node.identifier] = node
            return

        self._ensure_present(parent_id)
        node_id = node.identifier

        # map
        if self.get(parent_id)[1].keyed:
            if key is None:
                raise ValueError("Key is compulsory")
            if not isinstance(key, string_types):
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

    def _insert_node_above(self, node, child_id, key):
        self._ensure_present(child_id)
        parent_id = self.parent(child_id)
        child_subtree = self.drop_subtree(child_id)
        self._insert_node_below(node, parent_id, key=key)
        self._insert_tree_below(child_subtree, node.identifier, key=key)

    def insert_tree(
        self, new_tree, parent_id=None, child_id=None, child_id_below=None, key=None
    ):
        """Return new key"""
        self._validate_tree_insertion(new_tree)
        if new_tree.is_empty():
            return
        if parent_id is not None and child_id is not None:
            raise ValueError('Can declare at most "parent_id" or "child_id"')
        if child_id is not None:
            self._insert_tree_above(
                new_tree, child_id=child_id, child_id_below=child_id_below, key=key
            )
        else:
            self._insert_tree_below(new_tree, parent_id=parent_id, key=key)
        return self.get_key(new_tree.root)

    def _insert_tree_below(self, new_tree, parent_id, key):
        if parent_id is None:
            # insertion at root requires tree to be empty
            if not self.is_empty():
                raise MultipleRootError("A tree takes one root merely.")
        else:
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

    def _insert_tree_above(self, new_tree, child_id, child_id_below, key):
        # make all checks before modifying tree
        self._ensure_present(child_id)
        if child_id_below is not None:
            new_tree._ensure_present(child_id_below)
        else:
            new_tree_leaves = new_tree.leaves()
            if len(new_tree_leaves) > 1:
                raise ValueError(
                    'Ambiguous tree insertion, use "child_id_below" to specify under which node of new'
                    "tree you want to place existing nodes."
                )
            # by default take leaf if unique
            child_id_below = new_tree_leaves.pop()
        parent_id = self.parent(child_id)
        child_subtree = self.drop_subtree(child_id)
        self._insert_tree_below(new_tree, parent_id, key=key)
        self._insert_tree_below(child_subtree, child_id_below, key=key)

    def _drop_node(self, nid):
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
        return key, node

    def drop_node(self, nid, with_children=True):
        """If with_children is False, children of this node will take as new parent the dropped node parent.
        Possible only if node type is same as parent node type.

        Return key, node.
        """
        self._ensure_present(nid)

        children_ids = self.children_ids(nid)
        removed_key, removed_subtree = self.subtree(nid)
        if with_children:
            for cid in children_ids:
                self.drop_node(cid, with_children=True)
            return self._drop_node(nid)

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
            self._insert_tree_below(new_tree=st, parent_id=pid, key=k)
        return removed_key, removed_subtree.get(nid)[1]

    def drop_subtree(self, nid):
        self._ensure_present(nid)
        key, removed_subtree = self.subtree(nid)
        self.drop_node(nid=nid, with_children=True)
        return key, removed_subtree

    def expand_tree(
        self,
        nid=None,
        mode="depth",
        filter_=None,
        filter_through=False,
        sort_key=None,
        reverse=False,
    ):
        """Python generator traversing the tree (or a subtree) with optional node filtering.

        Inspired by treelib implementation https://github.com/caesar0301/treelib/blob/master/treelib/tree.py#L374

        :param nid: Node identifier from which tree traversal will start. If None tree root will be used
        :param mode: Traversal mode, may be either "depth" or "width"
        :param filter_: filter function performed on nodes. Node excluded from filter function won't be yielded.
        :param filter_through: if True, excluded nodes don't exclude their children.
        :param reverse: the ``reverse`` param for sorting :class:`Node` objects in the same level
        :param sort_key: key used to order nodes of same parent
        :return: node ids that satisfy the conditions if ``id_only`` is True, else nodes.
        :rtype: generator
        """
        if mode not in ("depth", "width"):
            raise NotImplementedError("Traversal mode '%s' is not supported" % mode)
        nid = self._ensure_present(nid, defaults_to_root=True, allow_empty=True)
        sort_key = itemgetter(0) if sort_key is None else sort_key
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
                queue.sort(key=sort_key, reverse=reverse)
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
                    expansion.sort(key=sort_key, reverse=reverse)
                    if mode == "depth":
                        queue = expansion + queue  # depth-first
                    elif mode == "width":
                        queue = queue + expansion  # width-first

    def show(
        self,
        nid=None,
        filter_=None,
        sort_key=None,
        reverse=False,
        line_type="ascii-ex",
        limit=None,
        **kwargs
    ):
        """Return tree structure in hierarchy style.

        :param nid: Node identifier from which tree traversal will start. If None tree root will be used
        :param filter\_: filter function performed on nodes. Nodes excluded from filter function nor their children won't be displayed
        :param reverse: the ``reverse`` param for sorting :class:`Node` objects in the same level
        :param sort_key: key used to order nodes of same parent
        :param reverse: reverse parameter applied at sorting
        :param line_type: display type choice
        :param limit: int, truncate tree display to this number of lines
        :param kwargs: kwargs params passed to node ``line_repr`` method
        :rtype: unicode in python2, str in python3

        """
        output = ""

        for is_last_list, key, node in self._iter_nodes_with_location(
            nid, filter_, sort_key, reverse
        ):
            prefix = self._prefix_repr(line_type, is_last_list)
            node_repr = node.line_repr(depth=len(is_last_list), **kwargs)
            output += "%s%s\n" % (prefix, node_repr)
            if limit is not None:
                limit -= 1
                if limit == 0:
                    output += "...\n(truncated, total number of nodes: %d)\n" % (
                        len(self._nodes_map.keys())
                    )
                    return output
        return output

    def _iter_nodes_with_location(
        self, nid, filter_, sort_key, reverse, is_last_list=None
    ):
        """Yield nodes with information on how they are placed.
        :param nid: starting node identifier
        :param filter_: filter function applied on nodes
        :param sort_key: key used to order nodes of same parent
        :param reverse: reverse parameter applied at sorting
        :param is_last_list: list of booleans, each indicating if node is the last yielded one at this depth
        :return: tuple of booleans, node
        """
        is_last_list = is_last_list or []
        sort_key = itemgetter(0) if sort_key is None else sort_key

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
                idxlast = len(children) - 1
                children.sort(key=sort_key, reverse=reverse)
                for idx, (child_k, child) in enumerate(children):
                    is_last_list.append(idx == idxlast)
                    for item in self._iter_nodes_with_location(
                        child.identifier, filter_, sort_key, reverse, is_last_list,
                    ):
                        yield item
                    is_last_list.pop()

    @staticmethod
    def _prefix_repr(line_type, is_last_list):
        if not is_last_list:
            return ""
        dt_vertical_line, dt_line_box, dt_line_corner = STYLES[line_type]
        leading = "".join(
            map(
                lambda x: dt_vertical_line + " " * 3 if not x else " " * 4,
                is_last_list[0:-1],
            )
        )
        lasting = dt_line_corner if is_last_list[-1] else dt_line_box
        return leading + lasting

    def merge(self, new_tree, nid=None):
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
        if not isinstance(new_tree, self.__class__):
            raise ValueError(
                'Wrong type of "new_tree", expected <%s>, got <%s>'
                % (self.__class__.__name__, new_tree.__class__.__name__)
            )

        if self.is_empty():
            return self._insert_tree_below(new_tree, parent_id=None)

        nid = self._ensure_present(nid, defaults_to_root=True)

        for ckey, cnode in new_tree.children(new_tree.root):
            self._insert_tree_below(
                new_tree.subtree(cnode.identifier)[1], nid, key=ckey
            )
        return self

    def __str__(self):
        return self.show()

    def __repr__(self):
        return self.__str__()

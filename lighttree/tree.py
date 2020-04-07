#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from future.utils import python_2_unicode_compatible, iteritems

from collections import defaultdict
from copy import deepcopy
from operator import attrgetter

from .node import Node
from .utils import STYLES
from .exceptions import MultipleRootError, NotFoundNodeError, DuplicatedNodeError


@python_2_unicode_compatible
class Tree(object):

    node_class = Node

    def __init__(self):
        # nodes references and hierarchy in tree
        self.root = None
        # node identifier -> node
        self._nodes_map = {}
        # node identifier -> parent node identifier
        self._nodes_parent = defaultdict(lambda: None)
        # node identifier -> children nodes identifiers
        self._nodes_children = defaultdict(set)

    def __contains__(self, identifier):
        return identifier in self._nodes_map

    def get(self, nid):
        """Get a node by its id."""
        self._ensure_present(nid)
        return self._nodes_map[nid]

    def list(self, id_in=None, depth_in=None, filter_=None):
        return [
            node
            for nid, node in iteritems(self._nodes_map)
            if (id_in is None or nid in id_in)
            and (filter_ is None or filter_(node))
            and (depth_in is None or self.depth(nid) in depth_in)
        ]

    def is_empty(self):
        """Return whether tree is empty (contains nodes) or not."""
        return self.root is None

    def _ensure_present(self, nid, defaults_to_root=False, allow_empty=False):
        if nid is None:
            if not self.is_empty() and defaults_to_root:
                return self.root
            if allow_empty:
                return None
            raise ValueError("'nid' set to None not supported.")
        if nid not in self._nodes_map:
            raise NotFoundNodeError("Node id <%s> doesn't exist in tree" % nid)
        return nid

    def _validate_node_insertion(self, node):
        if not isinstance(node, self.node_class):
            raise ValueError(
                "Node must be instance of <%s>, got <%s>."
                % (self.node_class.__name__, type(node))
            )
        if node.identifier in self._nodes_map.keys():
            raise DuplicatedNodeError(
                "Can't create node with id '%s'" % node.identifier
            )

    def _validate_tree_insertion(self, tree):
        if not isinstance(tree, self.__class__):
            raise ValueError(
                "Tree must be instance of <%s>, got <%s>"
                % (self.__class__.__name__, type(tree))
            )
        for node in tree.list():
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
        """
        return self.__class__()

    def _clone_nodes_with_hierarchy(self, new_tree, deep, new_root=None):
        """Clone nodes and node hierarchies from current tree to new tree."""
        self._validate_tree_insertion(new_tree)
        if new_root is not None:
            self._ensure_present(new_root)
        else:
            new_root = self.root
        for node in self.expand_tree(new_root, id_only=False):
            new_tree._nodes_map[node.identifier] = deepcopy(node) if deep else node
            new_tree._nodes_parent[node.identifier] = self._nodes_parent[
                node.identifier
            ]
            new_tree._nodes_children[node.identifier] = set(
                self._nodes_children[node.identifier]
            )

        new_tree.root = new_root
        new_tree._nodes_parent[new_root] = None
        return new_tree

    def clone(self, with_tree=True, deep=False, new_root=None):
        """Clone current instance, with or without tree.
        :rtype: :class:`ltree.Tree`
        """
        new_tree = self._clone_init(deep)
        if with_tree:
            self._clone_nodes_with_hierarchy(new_tree, new_root=new_root, deep=deep)
        return new_tree

    def parent(self, nid, id_only=True):
        """Return node parent id.
        Return None if given node id is root.
        """
        self._ensure_present(nid)
        if nid == self.root:
            return None
        id_ = self._nodes_parent[nid]
        if id_only:
            return id_
        return self.get(id_)

    def children(self, nid, id_only=True):
        """Return set of given node children node ids."""
        self._ensure_present(nid)
        # make a deep copy so that pointers cannot be mutated
        ids = set(self._nodes_children[nid])
        if id_only:
            return ids
        return {self.get(id_) for id_ in ids}

    def siblings(self, nid, id_only=True):
        """Return set of ids of nodes that share the provided node's parent."""
        self._ensure_present(nid)
        if nid == self.root:
            return set()
        pid = self.parent(nid, id_only=True)
        ids = self.children(pid, id_only=True).difference({nid})
        if id_only:
            return ids
        return {self.get(id_) for id_ in ids}

    def is_leaf(self, nid):
        """Return is node is a leaf in this tree."""
        return len(self.children(nid)) == 0

    def depth(self, nid):
        """Return node depth, 0 means root."""
        return len(self.ancestors(nid, id_only=True))

    def ancestors(self, nid, id_only=True, from_root=False):
        self._ensure_present(nid)
        if nid == self.root:
            return []
        ancestor_ids = []
        while nid != self.root:
            nid = self.parent(nid, id_only=True)
            ancestor_ids.append(nid)
        if from_root:
            ancestor_ids = list(reversed(ancestor_ids))
        if id_only:
            return ancestor_ids
        return [self.get(id_) for id_ in ancestor_ids]

    def subtree(self, nid, deep=False):
        return self.clone(with_tree=True, new_root=nid, deep=deep)

    def leaves(self, nid=None, id_only=True):
        """Return leaves under a node subtree."""
        tree = self if nid is None else self.subtree(nid)
        leaves_ids = {id_ for id_ in tree._nodes_map.keys() if tree.is_leaf(id_)}
        if id_only:
            return leaves_ids
        return {tree.get(id_) for id_ in leaves_ids}

    def insert(
        self, item, parent_id=None, child_id=None, deep=False, child_id_below=None
    ):
        if isinstance(item, Node):
            if child_id_below is not None:
                raise ValueError(
                    '"child_id_below" parameter is reserved to Tree insertion.'
                )
            self.insert_node(
                node=item, parent_id=parent_id, child_id=child_id, deep=deep
            )
            return self
        if isinstance(item, Tree):
            self.insert_tree(
                new_tree=item,
                parent_id=parent_id,
                child_id=child_id,
                deep=deep,
                child_id_below=child_id_below,
            )
            return self
        raise ValueError(
            '"item" parameter must either be a Node, or a Tree, got <%s>.' % type(item)
        )

    def insert_node(self, node, parent_id=None, child_id=None, deep=False):
        self._validate_node_insertion(node)
        node = deepcopy(node) if deep else node
        if parent_id is not None and child_id is not None:
            raise ValueError('Can declare at most "parent_id" or "child_id"')
        if parent_id is None and child_id is None:
            self._insert_node_at_root(node)
            return self
        if parent_id is not None:
            self._insert_node_below(node, parent_id=parent_id)
            return self
        self._insert_node_above(node, child_id=child_id)
        return self

    def _insert_node_at_root(self, node):
        if not self.is_empty():
            raise MultipleRootError("A tree takes one root merely.")
        self.root = node.identifier
        self._nodes_map[node.identifier] = node

    def _insert_node_below(self, node, parent_id):
        self._ensure_present(parent_id)
        node_id = node.identifier
        self._nodes_map[node_id] = node
        self._nodes_parent[node_id] = parent_id
        self._nodes_children[parent_id].add(node_id)

    def _insert_node_above(self, node, child_id):
        self._ensure_present(child_id)
        parent_id = self.parent(child_id)
        child_subtree = self.drop_subtree(child_id)
        if parent_id is None:
            self._insert_node_at_root(node)
        else:
            self._insert_node_below(node, parent_id)
        self._insert_tree_below(child_subtree, node.identifier, False)

    def insert_tree(
        self, new_tree, parent_id=None, child_id=None, deep=False, child_id_below=None
    ):
        self._validate_tree_insertion(new_tree)
        if new_tree.is_empty():
            raise ValueError("Inserted tree is empty")
        if parent_id is not None and child_id is not None:
            raise ValueError('Can declare at most "parent_id" or "child_id"')
        if parent_id is None and child_id is None:
            self._insert_tree_at_root(new_tree, deep=deep)
            return self
        if parent_id is not None:
            self._insert_tree_below(new_tree, parent_id=parent_id, deep=deep)
            return self
        self._insert_tree_above(
            new_tree, child_id=child_id, child_id_below=child_id_below, deep=deep
        )
        return self

    def _insert_tree_at_root(self, new_tree, deep):
        # replace tree, allowed only if initial tree is empty
        if not self.is_empty():
            raise MultipleRootError("A tree takes one root merely.")
        new_tree._clone_nodes_with_hierarchy(self, deep=deep)

    def _insert_tree_below(self, new_tree, parent_id, deep):
        self._validate_tree_insertion(new_tree)
        self._ensure_present(parent_id)

        if new_tree.is_empty():
            return self

        for new_nid in new_tree.expand_tree():
            node = new_tree.get(new_nid)
            pid = parent_id if new_nid == new_tree.root else new_tree.parent(new_nid)
            self.insert_node(deepcopy(node) if deep else node, parent_id=pid)

    def _insert_tree_above(self, new_tree, child_id, child_id_below, deep):
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
        if parent_id is None:
            self._insert_tree_at_root(new_tree, deep)
        else:
            self._insert_tree_below(new_tree, parent_id, deep)

        self._insert_tree_below(child_subtree, child_id_below, False)

    def _drop_node(self, nid):
        if self.children(nid):
            raise ValueError("Cannot drop node having children.")
        if nid == self.root:
            self.root = None
            return self._nodes_map.pop(nid)
        pid = self._nodes_parent.pop(nid)
        self._nodes_children.pop(nid)
        self._nodes_children[pid].remove(nid)
        return self._nodes_map.pop(nid)

    def drop_node(self, nid, with_children=True):
        """If with_children is False, children of this node will take as new parent the dropped node parent."""
        self._ensure_present(nid)

        children_ids = self.children(nid)
        removed_subtree = self.subtree(nid)
        if with_children:
            for cid in children_ids:
                self.drop_node(cid, with_children=True)
            return self._drop_node(nid)

        if nid == self.root and len(children_ids) > 1:
            raise MultipleRootError(
                "Cannot drop current root <%s> without its children, else tree would have "
                "multiple roots" % nid
            )
        pid = self.parent(nid)
        self.drop_node(nid, with_children=True)
        for cid in children_ids:
            self._insert_tree_below(removed_subtree.subtree(cid), pid, False)
        return removed_subtree.get(nid)

    def drop_subtree(self, nid):
        self._ensure_present(nid)
        removed_subtree = self.subtree(nid)
        self.drop_node(nid=nid, with_children=True)
        return removed_subtree

    def expand_tree(
        self,
        nid=None,
        mode="depth",
        filter_=None,
        key=None,
        reverse=False,
        id_only=True,
    ):
        """Python generator traversing the tree (or a subtree) with optional node filtering.

        Loosely based on an algorithm from 'Essential LISP' by John R. Anderson,
        Albert T. Corbett, and Brian J. Reiser, page 239-241, and inspired from treelib implementation.

        :param nid: Node identifier from which tree traversal will start. If None tree root will be used
        :param mode: Traversal mode, may be either "depth" or "width"
        :param filter_: filter function performed on nodes. Node excluded from filter function nor their children
        won't be yielded by generator.
        :param reverse: the ``reverse`` param for sorting :class:`Node` objects in the same level
        :param key: key used to order nodes of same parent
        :return: node ids that satisfy the conditions if ``id_only`` is True, else nodes.
        :rtype: generator
        """
        if mode not in ("depth", "width"):
            raise NotImplementedError("Traversal mode '%s' is not supported" % mode)
        nid = self._ensure_present(nid, defaults_to_root=True, allow_empty=True)
        key = attrgetter("identifier") if key is None else key
        if nid is not None:
            node = self.get(nid)
            if filter_ is None or filter_(node):
                yield nid if id_only else node
                queue = [
                    child_node
                    for child_node in self.children(nid, id_only=False)
                    if filter_ is None or filter_(child_node)
                ]
                queue.sort(key=key, reverse=reverse)
                while queue:
                    current_node = queue.pop(0)
                    yield current_node.identifier if id_only else current_node
                    expansion = [
                        gchild_node
                        for gchild_node in self.children(
                            current_node.identifier, id_only=False
                        )
                        if filter_ is None or filter_(gchild_node)
                    ]
                    expansion.sort(key=key, reverse=reverse)
                    if mode == "depth":
                        queue = expansion + queue  # depth-first
                    elif mode == "width":
                        queue = queue + expansion  # width-first

    def show(
        self,
        nid=None,
        filter_=None,
        key=None,
        reverse=False,
        line_type="ascii-ex",
        limit=None,
        **kwargs
    ):
        """Return tree structure in hierarchy style.

        :param nid: Node identifier from which tree traversal will start. If None tree root will be used
        :param filter_: filter function performed on nodes. Nodes excluded from filter function nor their children
        won't be displayed
        :param reverse: the ``reverse`` param for sorting :class:`Node` objects in the same level
        :param key: key used to order nodes of same parent
        :param reverse: reverse parameter applied at sorting
        :param line_type: display type choice
        :param limit: int, truncate tree display to this number of lines
        :param kwargs: kwargs params passed to node ``line_repr`` method
        :rtype: unicode in python2, str in python3
        """
        output = ""

        for depth, prefix, node in self._line_repr_iter(
            nid, filter_, key, reverse, line_type
        ):
            node_repr = node.line_repr(depth=depth, **kwargs)
            output += "%s%s\n" % (prefix, node_repr)
            if limit is not None:
                limit -= 1
                if limit == 0:
                    output += "...\n(truncated, total number of nodes: %d)\n" % (
                        len(self._nodes_map.keys())
                    )
                    return output
        return output

    def _line_repr_iter(
        self, nid, filter_, key, reverse, line_type, depth=0, is_last_list=None
    ):
        is_last_list = is_last_list or []
        key = attrgetter("identifier") if key is None else key

        nid = self._ensure_present(nid, defaults_to_root=True, allow_empty=True)
        if nid is not None:
            node = self.get(nid)
            if filter_ is None or filter_(node):
                prefix = self._prefix_repr(line_type, is_last_list)
                yield depth, prefix, node
                children = [
                    child_node
                    for child_node in self.children(nid, id_only=False)
                    if filter_ is None or filter_(child_node)
                ]
                idxlast = len(children) - 1
                children.sort(key=key, reverse=reverse)
                for idx, child in enumerate(children):
                    is_last_list.append(idx == idxlast)
                    for item in self._line_repr_iter(
                        child.identifier,
                        filter_,
                        key,
                        reverse,
                        line_type,
                        depth + 1,
                        is_last_list,
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

    def serialize(self, *args, **kwargs):
        return {
            "nodes_children": {
                nid: list(sorted(list(children_ids)))
                for nid, children_ids in iteritems(self._nodes_children)
                if children_ids
            },
            "nodes_parent": dict(self._nodes_parent),
            "node_class": ".".join(
                [self.node_class.__module__, self.node_class.__name__]
            ),
            "tree_class": ".".join(
                [self.__class__.__module__, self.__class__.__name__]
            ),
            "nodes_map": {
                nid: node.serialize(*args, **kwargs)
                for nid, node in iteritems(self._nodes_map)
            },
        }

    def merge(self, new_tree, nid=None, deep=False):
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

        >>>self.merge(new_tree, 'B')
        >>>self.show()
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
            new_tree._clone_nodes_with_hierarchy(new_tree=self, deep=deep)
            return self

        nid = self._ensure_present(nid, defaults_to_root=True)

        for cid in new_tree.children(new_tree.root):
            self._insert_tree_below(new_tree.subtree(cid), nid, deep=deep)
        return self

    def __str__(self):
        return self.show()

    def __repr__(self):
        return self.__str__()

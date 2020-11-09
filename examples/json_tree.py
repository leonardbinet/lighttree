from lighttree import TreeBasedObj
from lighttree.implementations.json_tree import JsonTree

if __name__ == '__main__':
    d = {
        "a": {
            "a": [
                "hello",
                "you"
            ],
            "b": 34,
            "c": "salut"
        },
        "c": [
            12,
            24,
            [
                "yo"
            ]
        ]
    }
    j = JsonTree(d)
    j.show()

    ij = TreeBasedObj(j)
    # display interactive representation
    ij
    # access subtree
    ij.a.b()

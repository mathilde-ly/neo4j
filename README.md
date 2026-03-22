# neo4j

A lightweight Python client for [Neo4j](https://neo4j.com/) that wraps the official [neo4j Python driver](https://pypi.org/project/neo4j/) and provides a simple interface for common graph database operations.

## Features

- Connect to any Neo4j instance via the Bolt protocol
- Create, read, update, and delete **nodes** with labels and arbitrary properties
- Create and query **relationships** between nodes
- Run arbitrary **Cypher** queries
- Works as a context manager for automatic connection cleanup

## Installation

```bash
pip install -r requirements.txt
```

## Quick start

```python
from neo4j_client import Neo4jClient

with Neo4jClient("bolt://localhost:7687", "neo4j", "password") as client:
    # Create nodes
    alice = client.create_node("Person", {"name": "Alice", "age": 30})
    bob   = client.create_node("Person", {"name": "Bob",   "age": 25})

    # Query nodes
    people = client.find_nodes("Person")

    # Update a node
    client.update_node("Person", {"name": "Alice"}, {"age": 31})

    # Create a relationship
    client.create_relationship(
        "Person", {"name": "Alice"},
        "Person", {"name": "Bob"},
        "KNOWS", {"since": 2020},
    )

    # Find relationships
    edges = client.find_relationships("Person", "Person", "KNOWS")

    # Run arbitrary Cypher
    results = client.run_query(
        "MATCH (n:Person) WHERE n.age > $min_age RETURN n",
        min_age=20,
    )

    # Delete a node
    client.delete_node("Person", name="Bob")
```

## API

| Method | Description |
|---|---|
| `create_node(label, properties)` | Create a node and return its properties |
| `find_nodes(label, **filters)` | Return nodes matching optional property filters |
| `update_node(label, match_props, update_props)` | Update matching nodes and return them |
| `delete_node(label, **match_props)` | Delete matching nodes; returns count deleted |
| `create_relationship(from_label, from_props, to_label, to_props, rel_type, rel_props)` | Create a relationship between two nodes |
| `find_relationships(from_label, to_label, rel_type)` | Return all matching relationships |
| `run_query(cypher, **params)` | Execute arbitrary Cypher and return a list of record dicts |

## Running the tests

```bash
python -m pytest tests/ -v
```
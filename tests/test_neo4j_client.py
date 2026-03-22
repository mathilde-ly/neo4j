"""Unit tests for Neo4jClient."""

from unittest.mock import MagicMock, patch

import pytest

from neo4j_client import Neo4jClient


@pytest.fixture
def mock_driver():
    with patch("neo4j_client.GraphDatabase.driver") as patched:
        driver = MagicMock()
        patched.return_value = driver
        yield driver


@pytest.fixture
def client(mock_driver):
    return Neo4jClient("bolt://localhost:7687", "neo4j", "password")


# ---------------------------------------------------------------------------
# Context-manager / lifecycle
# ---------------------------------------------------------------------------


def test_close_calls_driver_close(mock_driver):
    c = Neo4jClient("bolt://localhost:7687", "neo4j", "password")
    c.close()
    mock_driver.close.assert_called_once()


def test_context_manager_closes_driver(mock_driver):
    with Neo4jClient("bolt://localhost:7687", "neo4j", "password"):
        pass
    mock_driver.close.assert_called_once()


# ---------------------------------------------------------------------------
# create_node
# ---------------------------------------------------------------------------


def test_create_node_returns_node_data(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.__getitem__ = lambda self, key: {"name": "Alice", "age": 30}
    session.run.return_value.single.return_value = record

    result = client.create_node("Person", {"name": "Alice", "age": 30})

    session.run.assert_called_once_with(
        "CREATE (n:Person $props) RETURN n", props={"name": "Alice", "age": 30}
    )
    assert result == {"name": "Alice", "age": 30}


def test_create_node_returns_empty_when_no_record(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    session.run.return_value.single.return_value = None

    result = client.create_node("Person", {"name": "Bob"})

    assert result == {}


# ---------------------------------------------------------------------------
# find_nodes
# ---------------------------------------------------------------------------


def test_find_nodes_no_filters(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.__getitem__ = lambda self, key: {"name": "Alice"}
    session.run.return_value.__iter__ = lambda self: iter([record])

    result = client.find_nodes("Person")

    session.run.assert_called_once_with("MATCH (n:Person) RETURN n")
    assert result == [{"name": "Alice"}]


def test_find_nodes_with_filters(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    session.run.return_value.__iter__ = lambda self: iter([])

    client.find_nodes("Person", name="Alice")

    call_args = session.run.call_args
    assert "WHERE n.name = $name" in call_args[0][0]


# ---------------------------------------------------------------------------
# update_node
# ---------------------------------------------------------------------------


def test_update_node(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.__getitem__ = lambda self, key: {"name": "Alice", "age": 31}
    session.run.return_value.__iter__ = lambda self: iter([record])

    result = client.update_node("Person", {"name": "Alice"}, {"age": 31})

    assert result == [{"name": "Alice", "age": 31}]
    cypher = session.run.call_args[0][0]
    assert "SET n.age = $update_age" in cypher
    assert "WHERE n.name = $match_name" in cypher


# ---------------------------------------------------------------------------
# delete_node
# ---------------------------------------------------------------------------


def test_delete_node_returns_count(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.__getitem__ = lambda self, key: 1
    session.run.return_value.single.return_value = record

    result = client.delete_node("Person", name="Alice")

    assert result == 1
    cypher = session.run.call_args[0][0]
    assert "DETACH DELETE n" in cypher


def test_delete_node_returns_zero_when_no_record(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    session.run.return_value.single.return_value = None

    assert client.delete_node("Person", name="Ghost") == 0


# ---------------------------------------------------------------------------
# create_relationship
# ---------------------------------------------------------------------------


def test_create_relationship(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.__getitem__ = lambda self, key: {"since": 2020}
    session.run.return_value.single.return_value = record

    result = client.create_relationship(
        "Person", {"name": "Alice"},
        "Person", {"name": "Bob"},
        "KNOWS", {"since": 2020},
    )

    assert result == {"since": 2020}
    cypher = session.run.call_args[0][0]
    assert "CREATE (a)-[r:KNOWS $rel_props]->(b)" in cypher


def test_create_relationship_empty_from_props_raises(client):
    with pytest.raises(ValueError, match="from_props"):
        client.create_relationship("Person", {}, "Person", {"name": "Bob"}, "KNOWS")


def test_create_relationship_empty_to_props_raises(client):
    with pytest.raises(ValueError, match="to_props"):
        client.create_relationship("Person", {"name": "Alice"}, "Person", {}, "KNOWS")


def test_create_relationship_no_rel_props(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.__getitem__ = lambda self, key: {}
    session.run.return_value.single.return_value = record

    result = client.create_relationship(
        "Person", {"name": "Alice"},
        "Person", {"name": "Bob"},
        "KNOWS",
    )

    assert result == {}


# ---------------------------------------------------------------------------
# find_relationships
# ---------------------------------------------------------------------------


def test_find_relationships(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.__getitem__ = MagicMock(side_effect=lambda key: {
        "a": {"name": "Alice"},
        "r": {"since": 2020},
        "b": {"name": "Bob"},
    }[key])
    session.run.return_value.__iter__ = lambda self: iter([record])

    result = client.find_relationships("Person", "Person", "KNOWS")

    assert result == [{"from": {"name": "Alice"}, "rel": {"since": 2020}, "to": {"name": "Bob"}}]


# ---------------------------------------------------------------------------
# run_query
# ---------------------------------------------------------------------------


def test_run_query(client, mock_driver):
    session = mock_driver.session.return_value.__enter__.return_value
    record = MagicMock()
    record.data.return_value = {"n": {"name": "Alice"}}
    session.run.return_value.__iter__ = lambda self: iter([record])

    result = client.run_query("MATCH (n:Person) RETURN n", name="Alice")

    session.run.assert_called_once_with("MATCH (n:Person) RETURN n", name="Alice")
    assert result == [{"n": {"name": "Alice"}}]

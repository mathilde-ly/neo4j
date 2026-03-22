"""Neo4j client providing a simple interface for common graph operations."""

from neo4j import GraphDatabase


class Neo4jClient:
    """Manages a connection to a Neo4j database and exposes CRUD helpers."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Close the underlying driver connection."""
        self._driver.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def create_node(self, label: str, properties: dict) -> dict:
        """Create a node with *label* and *properties*, return the node data."""
        query = f"CREATE (n:{label} $props) RETURN n"
        with self._driver.session() as session:
            result = session.run(query, props=properties)
            record = result.single()
            return dict(record["n"]) if record else {}

    def find_nodes(self, label: str, **filters) -> list:
        """Return all nodes matching *label* and optional property *filters*."""
        where_clause = ""
        if filters:
            conditions = " AND ".join(f"n.{k} = ${k}" for k in filters)
            where_clause = f" WHERE {conditions}"
        query = f"MATCH (n:{label}){where_clause} RETURN n"
        with self._driver.session() as session:
            result = session.run(query, **filters)
            return [dict(record["n"]) for record in result]

    def update_node(self, label: str, match_props: dict, update_props: dict) -> list:
        """Update nodes matching *match_props* with *update_props*, return updated nodes."""
        conditions = " AND ".join(f"n.{k} = $match_{k}" for k in match_props)
        set_clause = ", ".join(f"n.{k} = $update_{k}" for k in update_props)
        params = {f"match_{k}": v for k, v in match_props.items()}
        params.update({f"update_{k}": v for k, v in update_props.items()})
        query = f"MATCH (n:{label}) WHERE {conditions} SET {set_clause} RETURN n"
        with self._driver.session() as session:
            result = session.run(query, **params)
            return [dict(record["n"]) for record in result]

    def delete_node(self, label: str, **match_props) -> int:
        """Delete all nodes matching *label* and *match_props*, return count deleted."""
        conditions = " AND ".join(f"n.{k} = ${k}" for k in match_props)
        query = (
            f"MATCH (n:{label}) WHERE {conditions} "
            "DETACH DELETE n RETURN count(n) AS deleted"
        )
        with self._driver.session() as session:
            result = session.run(query, **match_props)
            record = result.single()
            return record["deleted"] if record else 0

    # ------------------------------------------------------------------
    # Relationship operations
    # ------------------------------------------------------------------

    def create_relationship(
        self,
        from_label: str,
        from_props: dict,
        to_label: str,
        to_props: dict,
        rel_type: str,
        rel_props: dict | None = None,
    ) -> dict:
        """Create a relationship between two nodes and return its properties.

        *from_props* and *to_props* are used to match the source and target
        nodes respectively.  At least one property must be provided for each
        end so that the MATCH clause is unambiguous.
        """
        if not from_props:
            raise ValueError("from_props must contain at least one property to match the source node")
        if not to_props:
            raise ValueError("to_props must contain at least one property to match the target node")

        rel_props = rel_props or {}
        from_conditions = " AND ".join(f"a.{k} = $from_{k}" for k in from_props)
        to_conditions = " AND ".join(f"b.{k} = $to_{k}" for k in to_props)
        query = (
            f"MATCH (a:{from_label}), (b:{to_label}) "
            f"WHERE {from_conditions} AND {to_conditions} "
            f"CREATE (a)-[r:{rel_type} $rel_props]->(b) RETURN r"
        )
        params = {f"from_{k}": v for k, v in from_props.items()}
        params.update({f"to_{k}": v for k, v in to_props.items()})
        params["rel_props"] = rel_props
        with self._driver.session() as session:
            result = session.run(query, **params)
            record = result.single()
            return dict(record["r"]) if record else {}

    def find_relationships(
        self,
        from_label: str,
        to_label: str,
        rel_type: str,
    ) -> list:
        """Return all relationships of *rel_type* between *from_label* and *to_label*."""
        query = (
            f"MATCH (a:{from_label})-[r:{rel_type}]->(b:{to_label}) "
            "RETURN a, r, b"
        )
        with self._driver.session() as session:
            result = session.run(query)
            return [
                {"from": dict(record["a"]), "rel": dict(record["r"]), "to": dict(record["b"])}
                for record in result
            ]

    # ------------------------------------------------------------------
    # Generic Cypher execution
    # ------------------------------------------------------------------

    def run_query(self, cypher: str, **params) -> list:
        """Execute an arbitrary Cypher *query* and return a list of record dicts."""
        with self._driver.session() as session:
            result = session.run(cypher, **params)
            return [record.data() for record in result]

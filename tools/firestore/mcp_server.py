#!/usr/bin/env python3
"""
Custom MCP Server for Firestore Operations

Provides optimized Firestore query tools with automatic filtering
and field selection to reduce token usage.
"""
import sys
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from google.cloud import firestore
except ImportError:
    firestore = None

def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError (f"Type {type(obj)} not serializable")

def get_document(collection: str, doc_id: str) -> Dict[str, Any]:
    """
    Get a single document by its ID from a Firestore collection.

    Args:
        collection: Collection name.
        doc_id: The ID of the document to retrieve.

    Returns:
        The document data or an error.
    """
    if firestore is None:
        return {"error": "google-cloud-firestore not installed"}
    try:
        db = firestore.Client()
        doc_ref = db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        else:
            return {"error": f"Document with ID '{doc_id}' not found in collection '{collection}'."}
    except Exception as e:
        return {"error": str(e)}

def query_firestore(
    collection: str,
    filters: Optional[List[Dict[str, Any]]] = None,
    limit: int = 10,
    fields: Optional[List[str]] = None,
    order_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query Firestore with filtering and field selection.

    Args:
        collection: Collection name
        filters: List of filter conditions [{"field": "status", "op": "==", "value": "active"}]
        limit: Maximum number of results
        fields: Fields to return (reduces token usage)
        order_by: Field to order by

    Returns:
        Filtered and summarized results
    """
    if firestore is None:
        return {"error": "google-cloud-firestore not installed"}

    try:
        db = firestore.Client()
        query = db.collection(collection)

        if filters:
            for f in filters:
                query = query.where(f["field"], f["op"], f["value"])
        if order_by:
            query = query.order_by(order_by)
        if limit:
            query = query.limit(limit)

        docs = list(query.stream())
        results = []
        for doc in docs:
            data = doc.to_dict()
            if fields:
                data = {k: data.get(k) for k in fields if k in data}
            results.append({"id": doc.id, **data})

        return {"count": len(results), "data": results, "collection": collection}
    except Exception as e:
        return {"error": str(e)}

# MCP Protocol Handler
def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "firestore_get_document",
                    "description": "Get a single document by its ID from a Firestore collection.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "collection": {"type": "string", "description": "Collection name."},
                            "doc_id": {"type": "string", "description": "The ID of the document to retrieve."}
                        },
                        "required": ["collection", "doc_id"]
                    }
                },
                {
                    "name": "firestore_query",
                    "description": "Query Firestore with filtering and field selection to reduce token usage.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "collection": {"type": "string", "description": "Collection name"},
                            "filters": {
                                "type": "array",
                                "description": "Filter conditions",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {"type": "string"},
                                        "op": {"type": "string", "enum": ["==", "!=", "<", "<=", ">", ">=", "in", "array-contains"]},
                                        "value": {"description": "Filter value"}
                                    }
                                }
                            },
                            "limit": {"type": "integer", "default": 10},
                            "fields": {"type": "array", "items": {"type": "string"}},
                            "order_by": {"type": "string"}
                        },
                        "required": ["collection"]
                    }
                }
            ]
        }

    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "firestore_get_document":
            return get_document(**arguments)
        elif tool_name == "firestore_query":
            return query_firestore(**arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    else:
        return {"error": f"Unknown method: {method}"}

if __name__ == "__main__":
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, default=json_serializer))
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response, default=json_serializer))
            sys.stdout.flush()
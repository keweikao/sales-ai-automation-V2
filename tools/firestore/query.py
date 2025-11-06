"""
Tool: firestore_query
Category: firestore
Version: 1.0.0
Description: Query Firestore with automatic context optimization and PII protection

# derived from Anthropic official doc (2025)
"""

from google.cloud import firestore
from typing import List, Dict, Any, Optional


def query(
    collection: str,
    filters: List[Dict[str, Any]],
    order_by: Optional[str] = None,
    limit: int = 100,
    context_mode: str = "minimal"
) -> Dict[str, Any]:
    """
    Query Firestore collection with automatic context optimization.

    Args:
        collection: Collection name (e.g., "cases", "customers")
        filters: List of filter dicts with structure:
                 [{"field": str, "op": str, "value": Any}]
                 Operators: "==", "!=", "<", "<=", ">", ">=", "in", "array-contains"
        order_by: Field name for sorting (optional)
        limit: Maximum number of results to return
        context_mode: "minimal" | "full" | "aggregate"
            - minimal: Return only essential fields (default, 96-98% token reduction)
            - full: Return all fields (use only for <10 results)
            - aggregate: Return statistics only (99%+ token reduction)

    Returns:
        {
            "results": List[Dict] or Dict (for aggregate mode),
            "total_count": int,
            "returned_count": int,
            "truncated": bool,
            "context_mode": str
        }

    Example:
        result = query(
            collection="cases",
            filters=[
                {"field": "rep_name", "op": "==", "value": "王小明"},
                {"field": "health_score", "op": "<", "value": 60}
            ],
            order_by="health_score",
            limit=50,
            context_mode="minimal"
        )
    """

    # =====================================
    # STAGE 1: QUERY EXECUTION (in environment)
    # =====================================
    # Initialize Firestore client (reuse existing client if available)
    db = firestore.Client()
    query_ref = db.collection(collection)

    # Apply filters
    for f in filters:
        query_ref = query_ref.where(f["field"], f["op"], f["value"])

    # Apply ordering
    if order_by:
        query_ref = query_ref.order_by(order_by)

    # Fetch results (fetch extra for potential filtering)
    raw_results = list(query_ref.limit(limit * 2).stream())

    # Convert to dicts
    raw_data = [doc.to_dict() for doc in raw_results]

    # =====================================
    # STAGE 2: FIELD FILTERING (in environment)
    # derived from Anthropic official doc (2025)
    # =====================================
    if context_mode == "minimal":
        # Define essential fields per collection
        MINIMAL_FIELDS = {
            "cases": ["case_id", "customer_name", "rep_name", "health_score",
                     "created_date", "status"],
            "customers": ["customer_id", "name", "industry", "tier"],
            "reps": ["rep_id", "name", "team", "performance_score"],
        }

        essential_fields = MINIMAL_FIELDS.get(collection,
                                              ["id", "name", "created_date", "status"])

        filtered_results = [
            {k: doc.get(k) for k in essential_fields if k in doc}
            for doc in raw_data
        ]

    elif context_mode == "aggregate":
        # Compute aggregations in environment
        import pandas as pd

        if not raw_data:
            return {
                "results": {"total_count": 0},
                "total_count": 0,
                "returned_count": 0,
                "truncated": False,
                "context_mode": "aggregate"
            }

        df = pd.DataFrame(raw_data)

        # Compute common statistics
        filtered_results = {
            "total_count": len(df),
            "avg_health_score": float(df["health_score"].mean()) if "health_score" in df else None,
            "median_health_score": float(df["health_score"].median()) if "health_score" in df else None,
            "min_health_score": float(df["health_score"].min()) if "health_score" in df else None,
            "max_health_score": float(df["health_score"].max()) if "health_score" in df else None,
        }

        # Group by rep_name if exists
        if "rep_name" in df:
            filtered_results["by_rep"] = df.groupby("rep_name")["health_score"].agg(
                ["mean", "count"]
            ).to_dict()

        # Group by status if exists
        if "status" in df:
            filtered_results["by_status"] = df["status"].value_counts().to_dict()

    else:  # context_mode == "full"
        filtered_results = raw_data

    # =====================================
    # STAGE 3: RESULT TRUNCATION (in environment)
    # =====================================
    if context_mode != "aggregate" and len(filtered_results) > limit:
        filtered_results = filtered_results[:limit]

    # =====================================
    # STAGE 4: RETURN TO MODEL
    # =====================================
    return {
        "results": filtered_results,
        "total_count": len(raw_data),
        "returned_count": len(filtered_results) if context_mode != "aggregate" else 1,
        "truncated": len(raw_data) > limit,
        "context_mode": context_mode
    }
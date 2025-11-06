"""
Tool: bigquery_query
Category: bigquery
Version: 1.0.0
Description: Run a BigQuery query.

# derived from Google Cloud official doc (2025)
"""

from google.cloud import bigquery
from typing import Dict, Any

def query(query_string: str) -> Dict[str, Any]:
    """
    Runs a BigQuery query and returns the results.

    Args:
        query_string: The BigQuery query to execute.

    Returns:
        A dictionary with the query results.
    """

    try:
        client = bigquery.Client()
        query_job = client.query(query_string)
        results = query_job.result()  # Waits for the job to complete.

        rows = [dict(row) for row in results]

        return {
            "status": "success",
            "results": rows,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

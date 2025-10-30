#!/usr/bin/env python3
"""
POC 5: Firestore Query Performance & Cost Test
Tests Firestore query performance and monthly cost projection.

Success Criteria:
- Query latency <300ms (95th percentile)
- Monthly cost <$5 (for 250 files/month)
- Write latency <100ms
- Read latency <50ms

Requirements:
- GCP project with Firestore enabled
- Service account key with Firestore permissions
- Python 3.9+
- google-cloud-firestore package
"""

import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import statistics
import uuid

from google.cloud import firestore
from google.oauth2 import service_account

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class OperationMetrics:
    """Metrics for a single Firestore operation"""
    operation_id: str
    operation_type: str  # write, read, query, update
    collection: str
    latency_ms: float
    success: bool
    document_count: int = 1
    error_message: str = None

@dataclass
class CostEstimate:
    """Firestore cost estimation"""
    reads: int
    writes: int
    deletes: int
    storage_gb: float
    read_cost: float
    write_cost: float
    delete_cost: float
    storage_cost: float
    total_cost: float

@dataclass
class TestResults:
    """Overall test results"""
    total_operations: int
    successful_operations: int
    failed_operations: int
    avg_write_latency_ms: float
    avg_read_latency_ms: float
    avg_query_latency_ms: float
    p50_query_latency_ms: float
    p95_query_latency_ms: float
    p99_query_latency_ms: float
    estimated_monthly_cost: CostEstimate
    passed: bool
    details: List[OperationMetrics]

class FirestorePerformanceTester:
    """Test Firestore performance and cost"""

    # Firestore pricing (as of 2025-01)
    PRICE_PER_READ = 0.06 / 100000  # $0.06 per 100K reads
    PRICE_PER_WRITE = 0.18 / 100000  # $0.18 per 100K writes
    PRICE_PER_DELETE = 0.02 / 100000  # $0.02 per 100K deletes
    PRICE_PER_GB_STORAGE = 0.18  # $0.18 per GB per month

    def __init__(self, project_id: str, credentials_path: str = None):
        """
        Initialize Firestore client

        Args:
            project_id: GCP project ID
            credentials_path: Path to service account JSON key (optional, uses default credentials if not provided)
        """
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.db = firestore.Client(project=project_id, credentials=credentials)
        else:
            self.db = firestore.Client(project=project_id)

        self.test_collection = f"poc_test_{uuid.uuid4().hex[:8]}"
        self.metrics: List[OperationMetrics] = []

        logger.info(f"Initialized Firestore client for project: {project_id}")
        logger.info(f"Test collection: {self.test_collection}")

    def _record_metric(self, metric: OperationMetrics):
        """Record operation metric"""
        self.metrics.append(metric)
        status = "✅" if metric.success else "❌"
        logger.info(f"[{metric.operation_id}] {metric.operation_type.upper()} {status} - {metric.latency_ms:.0f}ms")

    def test_write_performance(self, num_writes: int = 50) -> List[OperationMetrics]:
        """Test write operations performance"""
        logger.info(f"\n=== Test 1: Write Performance ({num_writes} documents) ===")

        results = []

        for i in range(num_writes):
            op_id = f"write_{i+1}"
            start_time = time.time()

            try:
                # Create sample analysis result document
                doc_ref = self.db.collection(self.test_collection).document(f"analysis_{i+1}")
                doc_data = {
                    "fileId": f"file_{i+1}",
                    "fileName": f"sales_call_{i+1}.m4a",
                    "status": "completed",
                    "createdAt": firestore.SERVER_TIMESTAMP,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                    "transcription": {
                        "text": "這是一段測試逐字稿內容" * 50,  # ~1KB
                        "speakers": [
                            {"speaker": "業務", "text": "您好"},
                            {"speaker": "客戶", "text": "你好"}
                        ],
                        "duration": 1200
                    },
                    "analysis": {
                        "participants": [
                            {"role": "決策者", "name": "張總", "decisionMakingPower": "high"}
                        ],
                        "sentiment": {"overall": "positive", "score": 85},
                        "needs": [{"product": "POS系統", "urgency": "high"}]
                    }
                }

                doc_ref.set(doc_data)

                latency = (time.time() - start_time) * 1000

                metric = OperationMetrics(
                    operation_id=op_id,
                    operation_type="write",
                    collection=self.test_collection,
                    latency_ms=latency,
                    success=True
                )

                self._record_metric(metric)
                results.append(metric)

                # Small delay to avoid rate limits
                time.sleep(0.05)

            except Exception as e:
                latency = (time.time() - start_time) * 1000
                logger.error(f"[{op_id}] Write failed: {e}")

                metric = OperationMetrics(
                    operation_id=op_id,
                    operation_type="write",
                    collection=self.test_collection,
                    latency_ms=latency,
                    success=False,
                    error_message=str(e)
                )

                self._record_metric(metric)
                results.append(metric)

        return results

    def test_read_performance(self, num_reads: int = 50) -> List[OperationMetrics]:
        """Test single document read performance"""
        logger.info(f"\n=== Test 2: Read Performance ({num_reads} reads) ===")

        results = []

        for i in range(num_reads):
            op_id = f"read_{i+1}"
            doc_id = f"analysis_{(i % 50) + 1}"  # Read from existing docs
            start_time = time.time()

            try:
                doc_ref = self.db.collection(self.test_collection).document(doc_id)
                doc = doc_ref.get()

                latency = (time.time() - start_time) * 1000

                metric = OperationMetrics(
                    operation_id=op_id,
                    operation_type="read",
                    collection=self.test_collection,
                    latency_ms=latency,
                    success=doc.exists
                )

                self._record_metric(metric)
                results.append(metric)

                time.sleep(0.02)

            except Exception as e:
                latency = (time.time() - start_time) * 1000
                logger.error(f"[{op_id}] Read failed: {e}")

                metric = OperationMetrics(
                    operation_id=op_id,
                    operation_type="read",
                    collection=self.test_collection,
                    latency_ms=latency,
                    success=False,
                    error_message=str(e)
                )

                self._record_metric(metric)
                results.append(metric)

        return results

    def test_query_performance(self, num_queries: int = 30) -> List[OperationMetrics]:
        """Test complex query performance"""
        logger.info(f"\n=== Test 3: Query Performance ({num_queries} queries) ===")

        results = []

        query_types = [
            ("status_filter", lambda: self.db.collection(self.test_collection).where("status", "==", "completed")),
            ("timestamp_range", lambda: self.db.collection(self.test_collection)
                .where("createdAt", ">=", datetime(2025, 1, 1))
                .where("createdAt", "<=", datetime(2025, 12, 31))),
            ("order_by_limit", lambda: self.db.collection(self.test_collection)
                .order_by("createdAt", direction=firestore.Query.DESCENDING).limit(10)),
        ]

        for i in range(num_queries):
            query_type, query_builder = query_types[i % len(query_types)]
            op_id = f"query_{query_type}_{i+1}"
            start_time = time.time()

            try:
                query = query_builder()
                docs = list(query.stream())

                latency = (time.time() - start_time) * 1000

                metric = OperationMetrics(
                    operation_id=op_id,
                    operation_type="query",
                    collection=self.test_collection,
                    latency_ms=latency,
                    success=True,
                    document_count=len(docs)
                )

                self._record_metric(metric)
                results.append(metric)

                time.sleep(0.1)

            except Exception as e:
                latency = (time.time() - start_time) * 1000
                logger.error(f"[{op_id}] Query failed: {e}")

                metric = OperationMetrics(
                    operation_id=op_id,
                    operation_type="query",
                    collection=self.test_collection,
                    latency_ms=latency,
                    success=False,
                    error_message=str(e)
                )

                self._record_metric(metric)
                results.append(metric)

        return results

    def test_update_performance(self, num_updates: int = 20) -> List[OperationMetrics]:
        """Test update operations performance"""
        logger.info(f"\n=== Test 4: Update Performance ({num_updates} updates) ===")

        results = []

        for i in range(num_updates):
            op_id = f"update_{i+1}"
            doc_id = f"analysis_{(i % 50) + 1}"
            start_time = time.time()

            try:
                doc_ref = self.db.collection(self.test_collection).document(doc_id)
                doc_ref.update({
                    "status": "updated",
                    "updatedAt": firestore.SERVER_TIMESTAMP
                })

                latency = (time.time() - start_time) * 1000

                metric = OperationMetrics(
                    operation_id=op_id,
                    operation_type="update",
                    collection=self.test_collection,
                    latency_ms=latency,
                    success=True
                )

                self._record_metric(metric)
                results.append(metric)

                time.sleep(0.05)

            except Exception as e:
                latency = (time.time() - start_time) * 1000
                logger.error(f"[{op_id}] Update failed: {e}")

                metric = OperationMetrics(
                    operation_id=op_id,
                    operation_type="update",
                    collection=self.test_collection,
                    latency_ms=latency,
                    success=False,
                    error_message=str(e)
                )

                self._record_metric(metric)
                results.append(metric)

        return results

    def estimate_monthly_cost(self, files_per_month: int = 250) -> CostEstimate:
        """
        Estimate monthly Firestore cost based on usage patterns

        Assumptions for 250 files/month:
        - 1 write per file (initial analysis result)
        - 2 updates per file (status updates)
        - 10 reads per file (Slack interactions, queries)
        - 5 queries per file (dashboard, search)
        - Average doc size: 5KB
        """
        # Operations per month
        writes = files_per_month * 1
        updates = files_per_month * 2  # Updates count as writes
        reads = files_per_month * 10
        queries = files_per_month * 5  # Each query counts as 1 read minimum
        deletes = 0  # Assume we keep all data

        total_writes = writes + updates
        total_reads = reads + queries

        # Storage
        avg_doc_size_kb = 5
        storage_gb = (files_per_month * avg_doc_size_kb) / (1024 * 1024)  # Convert KB to GB

        # Costs
        read_cost = total_reads * self.PRICE_PER_READ
        write_cost = total_writes * self.PRICE_PER_WRITE
        delete_cost = deletes * self.PRICE_PER_DELETE
        storage_cost = storage_gb * self.PRICE_PER_GB_STORAGE

        total_cost = read_cost + write_cost + delete_cost + storage_cost

        return CostEstimate(
            reads=total_reads,
            writes=total_writes,
            deletes=deletes,
            storage_gb=storage_gb,
            read_cost=read_cost,
            write_cost=write_cost,
            delete_cost=delete_cost,
            storage_cost=storage_cost,
            total_cost=total_cost
        )

    def cleanup_test_data(self):
        """Delete test collection"""
        logger.info(f"\n=== Cleanup: Deleting test collection {self.test_collection} ===")

        try:
            docs = self.db.collection(self.test_collection).stream()
            deleted = 0

            for doc in docs:
                doc.reference.delete()
                deleted += 1

            logger.info(f"Deleted {deleted} test documents")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def run_all_tests(self) -> TestResults:
        """Run all performance tests"""
        logger.info("Starting POC 5: Firestore Performance & Cost Tests")

        # Run tests
        write_metrics = self.test_write_performance(num_writes=50)
        read_metrics = self.test_read_performance(num_reads=50)
        query_metrics = self.test_query_performance(num_queries=30)
        update_metrics = self.test_update_performance(num_updates=20)

        # Calculate statistics
        write_latencies = [m.latency_ms for m in write_metrics if m.success]
        read_latencies = [m.latency_ms for m in read_metrics if m.success]
        query_latencies = [m.latency_ms for m in query_metrics if m.success]

        avg_write = statistics.mean(write_latencies) if write_latencies else 0
        avg_read = statistics.mean(read_latencies) if read_latencies else 0
        avg_query = statistics.mean(query_latencies) if query_latencies else 0

        if query_latencies:
            p50_query = statistics.median(query_latencies)
            p95_query = statistics.quantiles(query_latencies, n=20)[18] if len(query_latencies) > 1 else query_latencies[0]
            p99_query = statistics.quantiles(query_latencies, n=100)[98] if len(query_latencies) > 2 else query_latencies[-1]
        else:
            p50_query = p95_query = p99_query = 0

        # Estimate monthly cost
        monthly_cost = self.estimate_monthly_cost(files_per_month=250)

        # Success criteria
        passed = (
            avg_write < 100 and
            avg_read < 50 and
            p95_query < 300 and
            monthly_cost.total_cost < 5.0
        )

        total_ops = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)

        results = TestResults(
            total_operations=total_ops,
            successful_operations=successful,
            failed_operations=total_ops - successful,
            avg_write_latency_ms=avg_write,
            avg_read_latency_ms=avg_read,
            avg_query_latency_ms=avg_query,
            p50_query_latency_ms=p50_query,
            p95_query_latency_ms=p95_query,
            p99_query_latency_ms=p99_query,
            estimated_monthly_cost=monthly_cost,
            passed=passed,
            details=self.metrics
        )

        # Cleanup
        self.cleanup_test_data()

        return results

def print_results(results: TestResults):
    """Print test results"""
    print("\n" + "="*70)
    print("POC 5: Firestore Performance & Cost Test Results")
    print("="*70)
    print(f"\nOperations:")
    print(f"  Total: {results.total_operations}")
    print(f"  Successful: {results.successful_operations}")
    print(f"  Failed: {results.failed_operations}")
    print(f"\nLatency Statistics:")
    print(f"  Write (avg): {results.avg_write_latency_ms:.0f}ms")
    print(f"  Read (avg): {results.avg_read_latency_ms:.0f}ms")
    print(f"  Query (avg): {results.avg_query_latency_ms:.0f}ms")
    print(f"  Query (P50): {results.p50_query_latency_ms:.0f}ms")
    print(f"  Query (P95): {results.p95_query_latency_ms:.0f}ms")
    print(f"  Query (P99): {results.p99_query_latency_ms:.0f}ms")

    cost = results.estimated_monthly_cost
    print(f"\nEstimated Monthly Cost (250 files/month):")
    print(f"  Operations:")
    print(f"    - Reads: {cost.reads:,} (${cost.read_cost:.4f})")
    print(f"    - Writes: {cost.writes:,} (${cost.write_cost:.4f})")
    print(f"    - Deletes: {cost.deletes:,} (${cost.delete_cost:.4f})")
    print(f"  Storage: {cost.storage_gb:.4f} GB (${cost.storage_cost:.4f})")
    print(f"  Total: ${cost.total_cost:.2f}/month")

    print(f"\nSuccess Criteria:")
    print(f"  ✅ Write latency < 100ms: {'PASS' if results.avg_write_latency_ms < 100 else 'FAIL'} ({results.avg_write_latency_ms:.0f}ms)")
    print(f"  ✅ Read latency < 50ms: {'PASS' if results.avg_read_latency_ms < 50 else 'FAIL'} ({results.avg_read_latency_ms:.0f}ms)")
    print(f"  ✅ Query P95 < 300ms: {'PASS' if results.p95_query_latency_ms < 300 else 'FAIL'} ({results.p95_query_latency_ms:.0f}ms)")
    print(f"  ✅ Monthly cost < $5: {'PASS' if cost.total_cost < 5 else 'FAIL'} (${cost.total_cost:.2f})")

    print(f"\n{'✅ POC 5 PASSED' if results.passed else '❌ POC 5 FAILED'}")
    print("="*70 + "\n")

def save_results(results: TestResults, output_path: str):
    """Save results to JSON file"""
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_operations": results.total_operations,
            "successful_operations": results.successful_operations,
            "failed_operations": results.failed_operations,
            "avg_write_latency_ms": results.avg_write_latency_ms,
            "avg_read_latency_ms": results.avg_read_latency_ms,
            "avg_query_latency_ms": results.avg_query_latency_ms,
            "p95_query_latency_ms": results.p95_query_latency_ms,
            "estimated_monthly_cost": asdict(results.estimated_monthly_cost),
            "passed": results.passed
        },
        "details": [asdict(m) for m in results.details]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_path}")

def main():
    """Main test execution"""
    project_id = os.getenv("GCP_PROJECT_ID")
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not project_id:
        logger.error("Missing GCP_PROJECT_ID environment variable")
        return

    tester = FirestorePerformanceTester(project_id, credentials_path)
    results = tester.run_all_tests()

    print_results(results)

    output_path = os.path.join(os.path.dirname(__file__), "poc5_results.json")
    save_results(results, output_path)

if __name__ == "__main__":
    main()

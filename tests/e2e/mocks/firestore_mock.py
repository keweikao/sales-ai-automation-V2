"""
Mock Firestore implementation for E2E tests

提供內存版本的 Firestore，支援基本的 CRUD 操作和 Transaction。
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from unittest.mock import MagicMock
import copy


class MockDocumentSnapshot:
    """Mock Firestore Document Snapshot"""

    def __init__(self, document_id: str, data: Optional[Dict[str, Any]] = None):
        self.id = document_id
        self._data = data
        self.exists = data is not None
        self.reference = MagicMock()
        self.reference.id = document_id
        self.create_time = datetime.now() if data else None
        self.update_time = datetime.now() if data else None

    def to_dict(self) -> Optional[Dict[str, Any]]:
        """Return document data as dictionary"""
        if not self.exists:
            return None
        # Deep copy to prevent external modifications
        return copy.deepcopy(self._data)

    def get(self, field_path: str):
        """Get specific field value"""
        if not self.exists:
            return None
        keys = field_path.split(".")
        value = self._data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value


class MockDocumentReference:
    """Mock Firestore Document Reference"""

    def __init__(self, collection_ref, document_id: str):
        self.collection_ref = collection_ref
        self.id = document_id
        self.path = f"{collection_ref.path}/{document_id}"
        self._firestore = collection_ref._firestore

    def get(self) -> MockDocumentSnapshot:
        """Get document snapshot"""
        data = self._firestore._get_document(self.collection_ref.id, self.id)
        return MockDocumentSnapshot(self.id, data)

    def set(self, data: Dict[str, Any], merge: bool = False):
        """Set document data"""
        if merge:
            existing = self._firestore._get_document(self.collection_ref.id, self.id)
            if existing:
                merged_data = {**existing, **data}
                self._firestore._set_document(self.collection_ref.id, self.id, merged_data)
            else:
                self._firestore._set_document(self.collection_ref.id, self.id, data)
        else:
            self._firestore._set_document(self.collection_ref.id, self.id, data)
        return self

    def update(self, updates: Dict[str, Any]):
        """Update document fields"""
        existing = self._firestore._get_document(self.collection_ref.id, self.id)
        if not existing:
            raise Exception(f"Document {self.path} does not exist")

        # Handle nested field updates (e.g., "notification.status")
        updated_data = copy.deepcopy(existing)
        for key, value in updates.items():
            if "." in key:
                keys = key.split(".")
                target = updated_data
                for k in keys[:-1]:
                    if k not in target:
                        target[k] = {}
                    target = target[k]
                target[keys[-1]] = value
            else:
                updated_data[key] = value

        self._firestore._set_document(self.collection_ref.id, self.id, updated_data)
        return self

    def delete(self):
        """Delete document"""
        self._firestore._delete_document(self.collection_ref.id, self.id)
        return self

    def collection(self, collection_id: str):
        """Get subcollection"""
        # Subcollections not implemented for now
        raise NotImplementedError("Subcollections not supported in mock")


class MockCollectionReference:
    """Mock Firestore Collection Reference"""

    def __init__(self, firestore, collection_id: str):
        self._firestore = firestore
        self.id = collection_id
        self.path = collection_id

    def document(self, document_id: Optional[str] = None) -> MockDocumentReference:
        """Get document reference"""
        if document_id is None:
            # Auto-generate document ID
            document_id = f"auto_{datetime.now().timestamp()}"
        return MockDocumentReference(self, document_id)

    def add(self, data: Dict[str, Any]) -> tuple:
        """Add document with auto-generated ID"""
        doc_ref = self.document()
        doc_ref.set(data)
        return (datetime.now(), doc_ref)

    def stream(self):
        """Stream all documents in collection"""
        documents = self._firestore._get_collection(self.id)
        return [MockDocumentSnapshot(doc_id, data) for doc_id, data in documents.items()]

    def where(self, field: str, op: str, value: Any):
        """Simple where query (basic implementation)"""
        # For now, just return all documents - implement filtering if needed
        return self

    def limit(self, count: int):
        """Limit query results"""
        # Not implemented - just return self for chaining
        return self

    def order_by(self, field: str, direction: str = "ASCENDING"):
        """Order query results"""
        # Not implemented - just return self for chaining
        return self


class MockTransaction:
    """Mock Firestore Transaction"""

    def __init__(self, firestore):
        self._firestore = firestore
        self._operations = []
        self._in_transaction = False

    def __enter__(self):
        self._in_transaction = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Commit all operations
            for op_type, args, kwargs in self._operations:
                if op_type == "set":
                    args[0].set(*args[1:], **kwargs)
                elif op_type == "update":
                    args[0].update(*args[1:], **kwargs)
                elif op_type == "delete":
                    args[0].delete()
        self._in_transaction = False
        self._operations = []
        return False  # Don't suppress exceptions

    def get(self, doc_ref: MockDocumentReference) -> MockDocumentSnapshot:
        """Get document in transaction"""
        return doc_ref.get()

    def set(self, doc_ref: MockDocumentReference, data: Dict[str, Any], merge: bool = False):
        """Set document in transaction"""
        if self._in_transaction:
            self._operations.append(("set", (doc_ref, data), {"merge": merge}))
        else:
            doc_ref.set(data, merge=merge)

    def update(self, doc_ref: MockDocumentReference, updates: Dict[str, Any]):
        """Update document in transaction"""
        if self._in_transaction:
            self._operations.append(("update", (doc_ref, updates), {}))
        else:
            doc_ref.update(updates)

    def delete(self, doc_ref: MockDocumentReference):
        """Delete document in transaction"""
        if self._in_transaction:
            self._operations.append(("delete", (doc_ref,), {}))
        else:
            doc_ref.delete()


class MockFirestore:
    """Mock Firestore Client"""

    # Mock SERVER_TIMESTAMP
    SERVER_TIMESTAMP = datetime.now()

    def __init__(self):
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._transaction = None

    def collection(self, collection_id: str) -> MockCollectionReference:
        """Get collection reference"""
        if collection_id not in self._data:
            self._data[collection_id] = {}
        return MockCollectionReference(self, collection_id)

    def transaction(self) -> MockTransaction:
        """Create transaction"""
        return MockTransaction(self)

    def _get_collection(self, collection_id: str) -> Dict[str, Dict[str, Any]]:
        """Internal: Get all documents in collection"""
        return self._data.get(collection_id, {})

    def _get_document(self, collection_id: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Internal: Get document data"""
        return self._data.get(collection_id, {}).get(document_id)

    def _set_document(self, collection_id: str, document_id: str, data: Dict[str, Any]):
        """Internal: Set document data"""
        if collection_id not in self._data:
            self._data[collection_id] = {}
        # Replace SERVER_TIMESTAMP with actual timestamp
        processed_data = self._process_timestamps(data)
        self._data[collection_id][document_id] = processed_data

    def _delete_document(self, collection_id: str, document_id: str):
        """Internal: Delete document"""
        if collection_id in self._data and document_id in self._data[collection_id]:
            del self._data[collection_id][document_id]

    def _process_timestamps(self, data: Any) -> Any:
        """Replace SERVER_TIMESTAMP with actual timestamp"""
        if isinstance(data, dict):
            return {
                key: datetime.now() if value == MockFirestore.SERVER_TIMESTAMP else self._process_timestamps(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._process_timestamps(item) for item in data]
        else:
            return data

    def reset(self):
        """Reset all data (useful for test cleanup)"""
        self._data = {}

    def dump_data(self) -> Dict:
        """Dump all data (useful for debugging)"""
        return copy.deepcopy(self._data)


# For compatibility with google.cloud.firestore
firestore = MagicMock()
firestore.SERVER_TIMESTAMP = MockFirestore.SERVER_TIMESTAMP

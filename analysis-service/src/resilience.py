"""
Resilience utilities for Sales AI Automation System.

P1 Fixes:
- Circuit Breaker pattern for external API calls
- Firestore transaction helpers for atomic updates
- Rate Limiter (Token Bucket) for API throttling

Usage:
    from .resilience import circuit_breaker, atomic_update, rate_limit

    @circuit_breaker("gemini_api")
    @rate_limit("gemini_api", tokens=1)
    def call_gemini(prompt):
        ...

    atomic_update(db, case_ref, update_data)
"""

import logging
import time
from typing import Any, Callable, Dict, Optional
from functools import wraps
from google.cloud import firestore

logger = logging.getLogger(__name__)


# =============================================================================
# Circuit Breaker Pattern
# =============================================================================

class CircuitBreaker:
    """
    Simple Circuit Breaker implementation.
    
    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Circuit is tripped, requests fail fast
    - HALF_OPEN: Testing if service recovered
    
    Configuration:
    - failure_threshold: Number of failures before opening circuit (default: 5)
    - recovery_timeout: Seconds before attempting recovery (default: 30)
    - success_threshold: Successes needed to close circuit (default: 2)
    """
    
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"
    
    # Shared instances by name
    _instances: Dict[str, "CircuitBreaker"] = {}
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = self.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time: Optional[float] = None
    
    @classmethod
    def get_instance(cls, name: str, **kwargs) -> "CircuitBreaker":
        """Get or create a named circuit breaker instance."""
        if name not in cls._instances:
            cls._instances[name] = cls(name, **kwargs)
        return cls._instances[name]
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == self.CLOSED:
            return True
        
        if self.state == self.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.recovery_timeout:
                self.state = self.HALF_OPEN
                self.successes = 0
                logger.info(f"[CIRCUIT:{self.name}] Transitioning to HALF_OPEN")
                return True
            return False
        
        # HALF_OPEN: Allow limited requests
        return True
    
    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == self.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                self.state = self.CLOSED
                self.failures = 0
                logger.info(f"[CIRCUIT:{self.name}] Circuit CLOSED - service recovered")
        else:
            self.failures = 0  # Reset on success
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.state == self.HALF_OPEN:
            self.state = self.OPEN
            logger.warning(f"[CIRCUIT:{self.name}] Circuit OPEN - still failing")
        elif self.failures >= self.failure_threshold:
            self.state = self.OPEN
            logger.warning(f"[CIRCUIT:{self.name}] Circuit OPEN - threshold reached ({self.failures} failures)")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit state for monitoring."""
        return {
            "name": self.name,
            "state": self.state,
            "failures": self.failures,
            "successes": self.successes,
            "last_failure": self.last_failure_time,
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


def circuit_breaker(name: str, **kwargs):
    """
    Decorator to wrap function with circuit breaker protection.
    
    Usage:
        @circuit_breaker("gemini_api")
        def call_gemini(prompt):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kw):
            cb = CircuitBreaker.get_instance(name, **kwargs)
            
            if not cb.can_execute():
                logger.warning(f"[CIRCUIT:{name}] Request blocked - circuit is OPEN")
                raise CircuitOpenError(f"Circuit {name} is open, request blocked")
            
            try:
                result = func(*args, **kw)
                cb.record_success()
                return result
            except Exception as e:
                cb.record_failure()
                raise
        
        return wrapper
    return decorator


# =============================================================================
# Firestore Transaction Helpers
# =============================================================================

def atomic_update(
    db: firestore.Client,
    doc_ref: firestore.DocumentReference,
    update_data: Dict[str, Any],
    max_retries: int = 3,
) -> bool:
    """
    Perform atomic update using Firestore transaction.
    
    This ensures read-modify-write operations are atomic and prevents
    race conditions when multiple agents update the same document.
    
    Args:
        db: Firestore client
        doc_ref: Document reference to update
        update_data: Data to merge into document
        max_retries: Maximum transaction retries
        
    Returns:
        True if successful, False otherwise
    """
    @firestore.transactional
    def _update_in_transaction(transaction, ref, data):
        # Read current state
        snapshot = ref.get(transaction=transaction)
        
        # Write update (merge)
        transaction.set(ref, data, merge=True)
        
        return True
    
    try:
        transaction = db.transaction()
        result = _update_in_transaction(transaction, doc_ref, update_data)
        logger.info(f"[TRANSACTION] Atomic update successful for {doc_ref.path}")
        return result
    except Exception as e:
        logger.error(f"[TRANSACTION] Atomic update failed for {doc_ref.path}: {e}")
        return False


def atomic_read_update(
    db: firestore.Client,
    doc_ref: firestore.DocumentReference,
    update_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    max_retries: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Read document, apply update function, and write atomically.
    
    This is useful when the update depends on current document state.
    
    Args:
        db: Firestore client
        doc_ref: Document reference
        update_fn: Function that takes current data and returns updated data
        max_retries: Maximum transaction retries
        
    Returns:
        Updated data if successful, None otherwise
    """
    @firestore.transactional
    def _read_update_in_transaction(transaction, ref, fn):
        snapshot = ref.get(transaction=transaction)
        current_data = snapshot.to_dict() or {}
        
        # Apply update function
        updated_data = fn(current_data)
        
        # Write back
        transaction.set(ref, updated_data, merge=True)
        
        return updated_data
    
    try:
        transaction = db.transaction()
        result = _read_update_in_transaction(transaction, doc_ref, update_fn)
        logger.info(f"[TRANSACTION] Atomic read-update successful for {doc_ref.path}")
        return result
    except Exception as e:
        logger.error(f"[TRANSACTION] Atomic read-update failed for {doc_ref.path}: {e}")
        return None


# =============================================================================
# Health Check Utilities
# =============================================================================

def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """Get states of all circuit breakers for health monitoring."""
    return {
        name: cb.get_state()
        for name, cb in CircuitBreaker._instances.items()
    }


def reset_circuit(name: str) -> bool:
    """Manually reset a circuit breaker (for admin use)."""
    if name in CircuitBreaker._instances:
        cb = CircuitBreaker._instances[name]
        cb.state = CircuitBreaker.CLOSED
        cb.failures = 0
        cb.successes = 0
        logger.info(f"[CIRCUIT:{name}] Manually reset to CLOSED")
        return True
    return False


# =============================================================================
# Rate Limiter (Token Bucket Algorithm)
# =============================================================================

class RateLimiter:
    """
    Token Bucket Rate Limiter for API call throttling.
    
    Based on Gemini API limits:
    - Flash: 60 RPM (requests per minute)
    - Pro: 60 RPM
    
    Configuration:
    - max_tokens: Maximum tokens in bucket (burst capacity)
    - refill_rate: Tokens added per second
    """
    
    _instances: Dict[str, "RateLimiter"] = {}
    
    def __init__(
        self,
        name: str,
        max_tokens: int = 60,  # Max burst
        refill_rate: float = 1.0,  # Tokens per second (60/min)
    ):
        self.name = name
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = max_tokens
        self.last_refill = time.time()
    
    @classmethod
    def get_instance(cls, name: str, **kwargs) -> "RateLimiter":
        """Get or create a named rate limiter instance."""
        if name not in cls._instances:
            cls._instances[name] = cls(name, **kwargs)
        return cls._instances[name]
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def acquire(self, tokens: int = 1, wait: bool = True, timeout: float = 30.0) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            wait: If True, wait for tokens to become available
            timeout: Maximum time to wait (seconds)
            
        Returns:
            True if tokens acquired, False if not available
        """
        start_time = time.time()
        
        while True:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"[RATE:{self.name}] Acquired {tokens} tokens, {self.tokens:.1f} remaining")
                return True
            
            if not wait:
                logger.warning(f"[RATE:{self.name}] Rate limit exceeded, {self.tokens:.1f} tokens available")
                return False
            
            # Check timeout
            if time.time() - start_time >= timeout:
                logger.warning(f"[RATE:{self.name}] Timeout waiting for tokens")
                return False
            
            # Wait for tokens to refill
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate
            wait_time = min(wait_time, 1.0)  # Max 1 second wait per iteration
            
            logger.debug(f"[RATE:{self.name}] Waiting {wait_time:.2f}s for tokens")
            time.sleep(wait_time)
    
    def get_state(self) -> Dict[str, Any]:
        """Get current rate limiter state for monitoring."""
        self._refill()
        return {
            "name": self.name,
            "tokens": self.tokens,
            "max_tokens": self.max_tokens,
            "refill_rate": self.refill_rate,
        }


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded and wait=False."""
    pass


def rate_limit(name: str, tokens: int = 1, wait: bool = True, **kwargs):
    """
    Decorator to apply rate limiting to a function.
    
    Usage:
        @rate_limit("gemini_api", tokens=1)
        def call_gemini(prompt):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kw):
            rl = RateLimiter.get_instance(name, **kwargs)
            
            if not rl.acquire(tokens=tokens, wait=wait):
                raise RateLimitExceeded(f"Rate limit exceeded for {name}")
            
            return func(*args, **kw)
        
        return wrapper
    return decorator


def get_all_rate_limiter_states() -> Dict[str, Dict[str, Any]]:
    """Get states of all rate limiters for health monitoring."""
    return {
        name: rl.get_state()
        for name, rl in RateLimiter._instances.items()
    }


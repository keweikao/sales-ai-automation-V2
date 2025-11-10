#!/usr/bin/env python3
"""
Test Slack notification functionality.

This script tests the Slack notification without actually running analysis.
It creates mock analysis data in Firestore and triggers a notification.

Usage:
    export SLACK_BOT_TOKEN="xoxb-..."
    python test_slack_notification.py CASE_ID USER_EMAIL

Example:
    python test_slack_notification.py TEST_CASE_001 stephen.kao@ichef.com.tw
"""

import sys
import os
from google.cloud import firestore
from slack_sdk import WebClient

# Add src to path
sys.path.insert(0, 'src')

from slack_notifier import SlackNotifier


def create_mock_analysis_data(db, case_id: str, uploaded_by: str, status: str = 'completed'):
    """
    Create mock case with analysis data for testing.

    Args:
        db: Firestore client
        case_id: Case ID to create
        uploaded_by: User email
        status: 'completed', 'partial_success', or 'failed'
    """
    # Mock analysis data
    if status == 'completed':
        agents = {
            'agent1': {
                'status': 'success',
                'duration': 28.5,
                'retryCount': 0,
                'data': {'participants': []}
            },
            'agent2': {
                'status': 'success',
                'duration': 22.1,
                'retryCount': 0,
                'data': {'sentiment': 'positive'}
            },
            'agent3': {
                'status': 'success',
                'duration': 25.3,
                'retryCount': 0,
                'data': {'needs': []}
            },
            'agent4': {
                'status': 'success',
                'duration': 20.8,
                'retryCount': 0,
                'data': {'competitors': []}
            },
            'agent5': {
                'status': 'success',
                'duration': 23.2,
                'retryCount': 0,
                'data': {'questionnaire': {}}
            },
        }
    elif status == 'partial_success':
        agents = {
            'agent1': {
                'status': 'success',
                'duration': 28.5,
                'retryCount': 0,
                'data': {'participants': []}
            },
            'agent2': {
                'status': 'success',
                'duration': 22.1,
                'retryCount': 0,
                'data': {'sentiment': 'positive'}
            },
            'agent3': {
                'status': 'failed',
                'duration': 15.3,
                'retryCount': 2,
                'error': 'Gemini API rate limit exceeded',
                'errorType': 'retryable'
            },
            'agent4': {
                'status': 'success',
                'duration': 20.8,
                'retryCount': 0,
                'data': {'competitors': []}
            },
            'agent5': {
                'status': 'failed',
                'duration': 10.5,
                'retryCount': 2,
                'error': 'JSON parsing failed',
                'errorType': 'retryable'
            },
        }
    else:  # failed
        agents = {
            'agent1': {
                'status': 'failed',
                'duration': 10.5,
                'retryCount': 2,
                'error': 'Connection timeout',
                'errorType': 'retryable'
            },
            'agent2': {
                'status': 'failed',
                'duration': 8.3,
                'retryCount': 2,
                'error': 'API error',
                'errorType': 'retryable'
            },
            'agent3': {
                'status': 'success',
                'duration': 25.3,
                'retryCount': 0,
                'data': {'needs': []}
            },
            'agent4': {
                'status': 'failed',
                'duration': 7.8,
                'retryCount': 2,
                'error': 'Rate limit',
                'errorType': 'retryable'
            },
            'agent5': {
                'status': 'failed',
                'duration': 9.5,
                'retryCount': 2,
                'error': 'Parse error',
                'errorType': 'retryable'
            },
        }

    case_data = {
        'customerId': '123456-789012',
        'storeName': '測試餐廳 - Slack 通知測試',
        'uploadedBy': uploaded_by,
        'audioFileName': 'test_audio.m4a',
        'status': status,
        'createdAt': firestore.SERVER_TIMESTAMP,
        'updatedAt': firestore.SERVER_TIMESTAMP,
        'transcription': {
            'text': '這是測試用的轉錄文字...',
            'segments': [],
            'speakers': []
        },
        'analysis': {
            'status': status,
            'completedAt': firestore.SERVER_TIMESTAMP,
            'totalDuration': 45.2,
            'agents': agents
        }
    }

    # Write to Firestore
    case_ref = db.collection('cases').document(case_id)
    case_ref.set(case_data)

    print(f"✅ Created mock case: {case_id}")
    print(f"   Status: {status}")
    print(f"   Uploaded by: {uploaded_by}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_slack_notification.py CASE_ID USER_EMAIL [STATUS]")
        print("Example: python test_slack_notification.py TEST_001 user@example.com completed")
        print("\nSTATUS options: completed, partial_success, failed (default: completed)")
        sys.exit(1)

    case_id = sys.argv[1]
    user_email = sys.argv[2]
    status = sys.argv[3] if len(sys.argv) > 3 else 'completed'

    if status not in ['completed', 'partial_success', 'failed']:
        print(f"Invalid status: {status}")
        print("Must be: completed, partial_success, or failed")
        sys.exit(1)

    # Check environment
    slack_token = os.environ.get('SLACK_BOT_TOKEN')
    if not slack_token:
        print("❌ Error: SLACK_BOT_TOKEN environment variable not set")
        sys.exit(1)

    print("=" * 60)
    print("Slack Notification Test")
    print("=" * 60)

    # Initialize Firestore
    print("\n1. Initializing Firestore...")
    db = firestore.Client()

    # Create mock data
    print(f"\n2. Creating mock analysis data...")
    create_mock_analysis_data(db, case_id, user_email, status)

    # Initialize Slack notifier
    print("\n3. Initializing Slack notifier...")
    notifier = SlackNotifier(slack_token=slack_token, db=db)

    # Send notification
    print(f"\n4. Sending Slack notification to {user_email}...")
    success = notifier.send_analysis_notification(case_id)

    if success:
        print("\n✅ Notification sent successfully!")
        print(f"\nCheck the Slack DM for: {user_email}")
    else:
        print("\n❌ Failed to send notification")
        print("Check the logs above for errors")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

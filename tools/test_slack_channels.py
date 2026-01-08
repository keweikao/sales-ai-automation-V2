#!/usr/bin/env python3
"""
Test script to list Slack channels the bot can access.
"""

import asyncio
import os
import sys

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def main():
    """List accessible Slack channels."""
    print("=" * 60)
    print("Slack Channel Discovery")
    print("=" * 60)

    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        print("ERROR: SLACK_BOT_TOKEN not set")
        sys.exit(1)

    client = WebClient(token=slack_token)

    # Test auth
    print("\nTesting auth...")
    try:
        auth_response = client.auth_test()
        print(f"  Bot User: {auth_response['user']}")
        print(f"  Bot User ID: {auth_response['user_id']}")
        print(f"  Team: {auth_response['team']}")
    except SlackApiError as e:
        print(f"  Auth failed: {e.response['error']}")
        sys.exit(1)

    # List public channels
    print("\nPublic channels:")
    try:
        result = client.conversations_list(types="public_channel", limit=100)
        for channel in result["channels"]:
            member_marker = "✓" if channel.get("is_member") else " "
            print(f"  [{member_marker}] {channel['id']} - #{channel['name']}")
    except SlackApiError as e:
        print(f"  Error: {e.response['error']}")

    # List private channels the bot is in
    print("\nPrivate channels (bot is member):")
    try:
        result = client.conversations_list(types="private_channel", limit=100)
        for channel in result["channels"]:
            print(f"  [✓] {channel['id']} - #{channel['name']}")
    except SlackApiError as e:
        print(f"  Error: {e.response['error']}")

    # Try to get info about the target channel
    target_channel = "C0A4F762FE0"
    print(f"\nTarget channel info ({target_channel}):")
    try:
        result = client.conversations_info(channel=target_channel)
        channel = result["channel"]
        print(f"  Name: #{channel['name']}")
        print(f"  Is Member: {channel.get('is_member', False)}")
    except SlackApiError as e:
        print(f"  Error: {e.response['error']}")
        print("  --> Bot may need to be invited to this channel")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

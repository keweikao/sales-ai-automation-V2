"""
V1 to V2.1 Migration Helper

Assists with migrating code from V1 structure to V2.1.

Usage:
    python -m tools.migration.v1_to_v2_migrator --check
    python -m tools.migration.v1_to_v2_migrator --migrate analysis-service
"""

import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class MigrationMapping:
    """Defines source to destination mapping."""
    source: str
    destination: str
    status: str = "pending"  # pending, in_progress, completed, skipped


# Migration mappings from V1 to V2.1
MIGRATIONS = [
    # Analysis service agents
    MigrationMapping(
        "analysis-service/src/agents/agent1_context.py",
        "modules/03-sales-conversation/meddic/agents/context_agent.py"
    ),
    MigrationMapping(
        "analysis-service/src/agents/agent2_buyer.py",
        "modules/03-sales-conversation/meddic/agents/buyer_agent.py"
    ),
    MigrationMapping(
        "analysis-service/src/agents/agent3_seller.py",
        "modules/03-sales-conversation/meddic/agents/seller_agent.py"
    ),
    MigrationMapping(
        "analysis-service/src/agents/agent4_summary.py",
        "modules/03-sales-conversation/meddic/agents/summary_agent.py"
    ),
    MigrationMapping(
        "analysis-service/src/agents/agent5_coach.py",
        "modules/03-sales-conversation/coaching/coach_agent.py"
    ),
    MigrationMapping(
        "analysis-service/src/agents/agent6_crm_extractor.py",
        "modules/03-sales-conversation/meddic/agents/crm_agent.py"
    ),
    MigrationMapping(
        "analysis-service/src/orchestrator.py",
        "modules/03-sales-conversation/transcript_analyzer/orchestrator.py"
    ),

    # Transcription service
    MigrationMapping(
        "src/transcription/groq_whisper_pipeline.py",
        "infrastructure/services/transcription/providers/whisper.py"
    ),
    MigrationMapping(
        "src/transcription/pipeline.py",
        "infrastructure/services/transcription/providers/google_stt.py"
    ),
    MigrationMapping(
        "src/transcription/main.py",
        "infrastructure/services/transcription/routes.py"
    ),

    # Slack app
    MigrationMapping(
        "src/slack_app/main.py",
        "modules/03-sales-conversation/slack_bot/main.py"
    ),
    MigrationMapping(
        "src/slack_app/utils/file_pipeline.py",
        "modules/03-sales-conversation/slack_bot/utils/file_pipeline.py"
    ),

    # CRM service
    MigrationMapping(
        "crm-service/src/salesforce_client.py",
        "infrastructure/services/integration/salesforce/client.py"
    ),

    # Token tracker
    MigrationMapping(
        "src/slack_app/monitoring/token_tracker.py",
        "infrastructure/services/llm_gateway/tracking/token_tracker.py"
    ),
]


class V1ToV2Migrator:
    """Handles migration from V1 to V2.1 structure."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(".")

    def check_status(self) -> dict:
        """Check migration status for all mappings."""
        results = {
            "pending": [],
            "source_exists": [],
            "dest_exists": [],
            "both_exist": [],
        }

        for mapping in MIGRATIONS:
            source = self.project_root / mapping.source
            dest = self.project_root / mapping.destination

            source_exists = source.exists()
            dest_exists = dest.exists()

            if source_exists and dest_exists:
                results["both_exist"].append(mapping)
            elif source_exists:
                results["source_exists"].append(mapping)
            elif dest_exists:
                results["dest_exists"].append(mapping)
            else:
                results["pending"].append(mapping)

        return results

    def print_status(self):
        """Print migration status report."""
        status = self.check_status()

        print("\n" + "=" * 60)
        print("V1 → V2.1 Migration Status")
        print("=" * 60)

        print(f"\n✅ Ready to migrate ({len(status['source_exists'])}):")
        for m in status["source_exists"]:
            print(f"   {m.source}")
            print(f"   → {m.destination}")

        print(f"\n⚠️  Already migrated ({len(status['both_exist'])}):")
        for m in status["both_exist"]:
            print(f"   {m.source} (need to verify)")

        print(f"\n📁 Destination only ({len(status['dest_exists'])}):")
        for m in status["dest_exists"]:
            print(f"   {m.destination}")

        print(f"\n❓ Neither exists ({len(status['pending'])}):")
        for m in status["pending"]:
            print(f"   {m.source}")

        print("\n" + "=" * 60)

    def generate_migration_script(self) -> str:
        """Generate bash script for migration."""
        status = self.check_status()
        lines = ["#!/bin/bash", "", "# V1 to V2.1 Migration Script", ""]

        for mapping in status["source_exists"]:
            dest_dir = Path(mapping.destination).parent
            lines.append(f"mkdir -p {dest_dir}")
            lines.append(f"cp {mapping.source} {mapping.destination}")
            lines.append("")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="V1 to V2.1 Migration Helper")
    parser.add_argument("--check", action="store_true", help="Check migration status")
    parser.add_argument("--script", action="store_true", help="Generate migration script")

    args = parser.parse_args()
    migrator = V1ToV2Migrator()

    if args.check:
        migrator.print_status()
    elif args.script:
        print(migrator.generate_migration_script())
    else:
        migrator.print_status()


if __name__ == "__main__":
    main()

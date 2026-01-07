#!/usr/bin/env python3
"""
Gemini Model Version Manager

This tool helps manage and validate Gemini model versions across the codebase.
It prevents issues caused by Google's model version changes and deprecations.

Features:
1. Validate current model configurations
2. Test model availability
3. Auto-update to stable versions
4. Generate migration reports

Usage:
    python tools/gemini_model_manager.py validate
    python tools/gemini_model_manager.py test --model gemini-2.0-flash
    python tools/gemini_model_manager.py update --dry-run
    python tools/gemini_model_manager.py list-available
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google-generativeai not available. Install with: pip install google-generativeai")


@dataclass
class ModelConfig:
    """Configuration for a Gemini model."""
    name: str
    file_path: str
    line_number: int
    current_value: str
    context: str


# Model version mapping for automatic updates
MODEL_MIGRATIONS = {
    "gemini-1.5-flash": "gemini-2.0-flash",
    "gemini-1.5-flash-001": "gemini-2.0-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
    "gemini-pro": "gemini-2.0-flash",
}

# Known stable models (as of 2026-01)
STABLE_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
]

# Deprecated models that should be migrated
DEPRECATED_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
]


class GeminiModelManager:
    """Manage Gemini model versions across the codebase."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.api_key = os.getenv("GEMINI_API_KEY")

        if self.api_key and GENAI_AVAILABLE:
            genai.configure(api_key=self.api_key)

    def find_model_usages(self) -> List[ModelConfig]:
        """Scan codebase for Gemini model usages."""
        configs = []

        # Patterns to match model declarations
        patterns = [
            r'GEMINI_MODEL.*["\']([^"\']+)["\']',
            r'DEFAULT_MODEL_NAME\s*=\s*["\']([^"\']+)["\']',
            r'model_name\s*=\s*["\']([^"\']+)["\']',
            r'GenerativeModel\(["\']([^"\']+)["\']',
            r'genai\.GenerativeModel\(["\']([^"\']+)["\']',
        ]

        # Files to scan
        python_files = list(self.project_root.rglob("*.py"))
        yaml_files = list(self.project_root.rglob("*.yaml"))

        for file_path in python_files + yaml_files:
            # Skip virtual environments and node_modules
            if '.venv' in str(file_path) or 'node_modules' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in patterns:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            model_name = match.group(1)
                            # Filter for gemini models only
                            if 'gemini' in model_name.lower():
                                configs.append(ModelConfig(
                                    name=model_name,
                                    file_path=str(file_path.relative_to(self.project_root)),
                                    line_number=line_num,
                                    current_value=model_name,
                                    context=line.strip()
                                ))
            except Exception as e:
                print(f"⚠️  Error reading {file_path}: {e}")

        return configs

    def validate_models(self, configs: List[ModelConfig]) -> Dict[str, List[ModelConfig]]:
        """Categorize models as stable, deprecated, or unknown."""
        result = {
            "stable": [],
            "deprecated": [],
            "unknown": []
        }

        for config in configs:
            if config.name in STABLE_MODELS:
                result["stable"].append(config)
            elif config.name in DEPRECATED_MODELS:
                result["deprecated"].append(config)
            else:
                result["unknown"].append(config)

        return result

    def test_model(self, model_name: str) -> bool:
        """Test if a model is available and working."""
        if not self.api_key or not GENAI_AVAILABLE:
            print("⚠️  Cannot test model: GEMINI_API_KEY not set or genai not available")
            return False

        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Hello")
            print(f"✅ Model {model_name} is working")
            print(f"   Response: {response.text[:50]}...")
            return True
        except Exception as e:
            print(f"❌ Model {model_name} failed: {e}")
            return False

    def list_available_models(self) -> List[str]:
        """List all available Gemini models from API."""
        if not self.api_key or not GENAI_AVAILABLE:
            print("⚠️  Cannot list models: GEMINI_API_KEY not set or genai not available")
            return []

        try:
            models = genai.list_models()
            gemini_models = [
                m.name for m in models
                if 'gemini' in m.name.lower() and 'generateContent' in m.supported_generation_methods
            ]
            return gemini_models
        except Exception as e:
            print(f"❌ Failed to list models: {e}")
            return []

    def generate_migration_plan(self, configs: List[ModelConfig]) -> Dict[str, List[Dict]]:
        """Generate migration plan for deprecated models."""
        plan = []

        for config in configs:
            if config.name in MODEL_MIGRATIONS:
                new_model = MODEL_MIGRATIONS[config.name]
                plan.append({
                    "file": config.file_path,
                    "line": config.line_number,
                    "old_model": config.name,
                    "new_model": new_model,
                    "context": config.context
                })

        return {"migrations": plan}

    def update_models(self, dry_run: bool = True) -> int:
        """Update deprecated models to stable versions."""
        configs = self.find_model_usages()
        validation = self.validate_models(configs)

        if not validation["deprecated"]:
            print("✅ No deprecated models found!")
            return 0

        updates_count = 0

        for config in validation["deprecated"]:
            if config.name not in MODEL_MIGRATIONS:
                print(f"⚠️  No migration available for {config.name}")
                continue

            new_model = MODEL_MIGRATIONS[config.name]
            file_path = self.project_root / config.file_path

            print(f"\n{'[DRY RUN] ' if dry_run else ''}Updating {config.file_path}:{config.line_number}")
            print(f"  {config.name} → {new_model}")
            print(f"  Context: {config.context}")

            if not dry_run:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Replace old model with new model
                    updated_content = content.replace(
                        f'"{config.name}"',
                        f'"{new_model}"'
                    ).replace(
                        f"'{config.name}'",
                        f"'{new_model}'"
                    )

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)

                    print(f"  ✅ Updated successfully")
                    updates_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to update: {e}")

        return updates_count


def main():
    parser = argparse.ArgumentParser(
        description="Gemini Model Version Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Validate command
    subparsers.add_parser('validate', help='Validate model configurations')

    # Test command
    test_parser = subparsers.add_parser('test', help='Test a specific model')
    test_parser.add_argument('--model', required=True, help='Model name to test')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update deprecated models')
    update_parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')

    # List command
    subparsers.add_parser('list-available', help='List available models from API')

    # Migration plan command
    subparsers.add_parser('migration-plan', help='Generate migration plan')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize manager
    project_root = Path(__file__).parent.parent
    manager = GeminiModelManager(project_root)

    # Execute command
    if args.command == 'validate':
        print("🔍 Scanning codebase for Gemini model usages...\n")
        configs = manager.find_model_usages()
        validation = manager.validate_models(configs)

        print(f"\n📊 Found {len(configs)} model usages:\n")

        if validation["stable"]:
            print(f"✅ Stable models ({len(validation['stable'])}):")
            for config in validation["stable"]:
                print(f"   {config.file_path}:{config.line_number} - {config.name}")

        if validation["deprecated"]:
            print(f"\n⚠️  Deprecated models ({len(validation['deprecated'])}):")
            for config in validation["deprecated"]:
                suggested = MODEL_MIGRATIONS.get(config.name, "unknown")
                print(f"   {config.file_path}:{config.line_number} - {config.name} → {suggested}")

        if validation["unknown"]:
            print(f"\n❓ Unknown models ({len(validation['unknown'])}):")
            for config in validation["unknown"]:
                print(f"   {config.file_path}:{config.line_number} - {config.name}")

        if validation["deprecated"]:
            print(f"\n💡 Run 'python tools/gemini_model_manager.py update' to fix deprecated models")
            return 1

        return 0

    elif args.command == 'test':
        print(f"🧪 Testing model: {args.model}\n")
        success = manager.test_model(args.model)
        return 0 if success else 1

    elif args.command == 'update':
        print("🔧 Updating deprecated models...\n")
        updates = manager.update_models(dry_run=args.dry_run)

        if args.dry_run:
            print(f"\n💡 {updates} models would be updated. Run without --dry-run to apply changes.")
        else:
            print(f"\n✅ Updated {updates} models")

        return 0

    elif args.command == 'list-available':
        print("📋 Fetching available models from API...\n")
        models = manager.list_available_models()

        if models:
            print(f"Found {len(models)} Gemini models:\n")
            for model in models:
                stable = "✅" if any(stable in model for stable in STABLE_MODELS) else ""
                print(f"  {stable} {model}")

        return 0

    elif args.command == 'migration-plan':
        print("📋 Generating migration plan...\n")
        configs = manager.find_model_usages()
        validation = manager.validate_models(configs)
        plan = manager.generate_migration_plan(validation["deprecated"])

        print(json.dumps(plan, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

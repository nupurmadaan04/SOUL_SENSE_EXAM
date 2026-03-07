"""
CLI tools for Release Notes Generator
Commands: generate, auto-detect, publish, preview, validate, template
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infra.release_notes_generator import ReleaseNotesGenerator


def cmd_generate(args):
    """Generate release notes between specific tags"""
    gen = ReleaseNotesGenerator(args.repo_path)
    
    print(f"📋 Generating release notes from {args.from_tag} to {args.to_tag}...")
    notes = gen.generate_notes(args.version or args.from_tag, args.from_tag, args.to_tag)
    
    if args.format == "markdown":
        output = gen.format_markdown(notes)
    else:
        gen.export_json(notes, "release_notes.json")
        output = "✅ Release notes exported to release_notes.json"
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"✅ Saved to {args.output}")
    else:
        print(output)


def cmd_auto_detect(args):
    """Auto-detect latest tags and generate notes"""
    gen = ReleaseNotesGenerator(args.repo_path)
    
    print("🔍 Detecting latest tags...")
    tags = gen.get_tags()
    
    if len(tags) < 2:
        print("⚠️  Not enough tags found (need at least 2)")
        return
    
    latest_tag = tags[0]
    previous_tag = tags[1]
    
    print(f"📋 Found {len(tags)} tags. Latest: {latest_tag}, Previous: {previous_tag}")
    print(f"📝 Generating release notes...")
    
    notes = gen.generate_notes(latest_tag, previous_tag, latest_tag)
    
    markdown = gen.format_markdown(notes)
    filename = f"RELEASE_{latest_tag.replace('/', '_')}.md"
    
    with open(filename, 'w') as f:
        f.write(markdown)
    
    print(f"✅ Release notes generated: {filename}")
    print(f"\n{markdown}\n")


def cmd_publish(args):
    """Generate and append to CHANGELOG.md"""
    gen = ReleaseNotesGenerator(args.repo_path)
    
    tags = gen.get_tags()
    if not tags:
        print("⚠️  No tags found")
        return
    
    from_tag = tags[1] if len(tags) > 1 else tags[0]
    to_tag = tags[0]
    
    print(f"📝 Publishing release notes from {from_tag} to {to_tag}...")
    notes = gen.generate_notes(to_tag, from_tag, to_tag)
    
    if gen.save_to_file(notes, "CHANGELOG.md", append=True):
        print(f"✅ Published to CHANGELOG.md")
        print(f"   - Version: {notes.version}")
        print(f"   - Total commits: {notes.total_commits}")
        print(f"   - Contributors: {len(notes.contributors)}")
    else:
        print("❌ Failed to publish")


def cmd_preview(args):
    """Preview release notes without saving"""
    gen = ReleaseNotesGenerator(args.repo_path)
    
    print(f"👀 Previewing release notes from {args.from_tag} to {args.to_tag}...")
    notes = gen.generate_notes(args.version or "draft", args.from_tag, args.to_tag)
    
    markdown = gen.format_markdown(notes)
    print("\n" + "="*60)
    print(markdown)
    print("="*60 + "\n")
    
    print(f"Preview Summary:")
    print(f"  Features: {len(notes.features)}")
    print(f"  Bug Fixes: {len(notes.fixes)}")
    print(f"  Documentation: {len(notes.docs)}")
    print(f"  Breaking Changes: {len(notes.breaking_changes)}")
    print(f"  Contributors: {len(notes.contributors)}")


def cmd_validate(args):
    """Validate commit message format"""
    gen = ReleaseNotesGenerator(args.repo_path)
    
    commits = gen.get_commits_between(args.from_ref or "HEAD~20", "HEAD")
    
    print("🔍 Validating commit messages...")
    print(f"Checking {len(commits)} commits...\n")
    
    valid_count = 0
    invalid_count = 0
    
    for commit in commits:
        if commit.change_type in gen.CONFIG_TYPES:
            print(f"✅ {commit.message}")
            valid_count += 1
        else:
            print(f"⚠️  {commit.message} (not conventional)")
            invalid_count += 1
    
    print(f"\nSummary: {valid_count} valid, {invalid_count} non-conventional")


def cmd_template(args):
    """Show commit message template"""
    template = """
📋 COMMIT MESSAGE TEMPLATE

Format: type(scope): description

Examples:
  feat(auth): add JWT refresh token support
  fix(db): handle null values in migration
  docs(api): update endpoint documentation
  refactor(core): simplify middleware chain
  perf(query): optimize database indexes
  test(auth): add token expiration tests

Valid types: feat, fix, docs, refactor, perf, test, build, ci, chore, style

Breaking changes: Add ! before colon
  feat(api)!: redesign response format

Full example:
  feat(db): add connection pooling

  - Implements connection pool for better performance
  - Reduces database connection overhead by 40%
  - Backward compatible with existing code
"""
    print(template)


def cmd_list_tags(args):
    """List all available tags"""
    gen = ReleaseNotesGenerator(args.repo_path)
    
    tags = gen.get_tags()
    if not tags:
        print("No tags found")
        return
    
    print(f"📌 Found {len(tags)} tags:\n")
    for i, tag in enumerate(tags[:10], 1):
        print(f"  {i}. {tag}")
    
    if len(tags) > 10:
        print(f"  ... and {len(tags) - 10} more")


def main():
    parser = argparse.ArgumentParser(
        description="Release Notes Generator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Path to git repository (default: current directory)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # generate command
    gen_parser = subparsers.add_parser("generate", help="Generate release notes")
    gen_parser.add_argument("--from-tag", required=True, help="Starting tag")
    gen_parser.add_argument("--to-tag", default="HEAD", help="Ending tag/ref")
    gen_parser.add_argument("--version", help="Version number for notes")
    gen_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    gen_parser.add_argument("--output", help="Output file path")
    gen_parser.set_defaults(func=cmd_generate)
    
    # auto-detect command
    auto_parser = subparsers.add_parser("auto-detect", help="Auto-detect tags and generate")
    auto_parser.set_defaults(func=cmd_auto_detect)
    
    # publish command
    pub_parser = subparsers.add_parser("publish", help="Publish to CHANGELOG.md")
    pub_parser.set_defaults(func=cmd_publish)
    
    # preview command
    prev_parser = subparsers.add_parser("preview", help="Preview release notes")
    prev_parser.add_argument("--from-tag", required=True, help="Starting tag")
    prev_parser.add_argument("--to-tag", default="HEAD", help="Ending tag/ref")
    prev_parser.add_argument("--version", help="Version number")
    prev_parser.set_defaults(func=cmd_preview)
    
    # validate command
    val_parser = subparsers.add_parser("validate", help="Validate commit messages")
    val_parser.add_argument("--from-ref", help="Starting ref (default: HEAD~20)")
    val_parser.set_defaults(func=cmd_validate)
    
    # template command
    tpl_parser = subparsers.add_parser("template", help="Show commit message template")
    tpl_parser.set_defaults(func=cmd_template)
    
    # list-tags command
    list_parser = subparsers.add_parser("list-tags", help="List all git tags")
    list_parser.set_defaults(func=cmd_list_tags)
    
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

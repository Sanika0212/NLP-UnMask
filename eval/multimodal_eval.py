"""
Multimodal blind-test evaluation script.

Evaluates the vision model's ability to identify anatomical structures from diagrams.

Usage:
  python eval/multimodal_eval.py                    # Run full evaluation
  python eval/multimodal_eval.py --dry-run          # Preview without API calls

Ground truth: filename of each PNG → anatomical structure name
Model: Claude Opus (via OpenRouter) vision endpoint
Metrics: exact match accuracy, fuzzy match (words in response)
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()


def get_anatomy_png_files() -> dict[str, str]:
    """Return dict of {ground_truth_label: png_path} from public/anatomy/."""
    anatomy_dir = Path(__file__).parent.parent / "public" / "anatomy"
    png_files = sorted(anatomy_dir.glob("*.png"))

    result = {}
    for png_path in png_files:
        # Ground truth: filename without extension, replace underscores with spaces
        label = png_path.stem.replace("_", " ")
        result[label] = str(png_path)

    return result


def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_vision_model(image_path: str, base64_data: str) -> Optional[str]:
    """
    Call Claude Opus via OpenRouter with vision capabilities.

    Prompt: "What anatomical structure is shown in this diagram? Reply with the anatomical name only (2-5 words)."

    Returns: model response (anatomical name), or None on error.
    """
    from openai import OpenAI

    try:
        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
        )

        # Determine media type from extension
        ext = Path(image_path).suffix.lower()
        media_type_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
        media_type = media_type_map.get(ext, "image/png")

        response = client.chat.completions.create(
            model="anthropic/claude-opus-4",
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{base64_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "What anatomical structure is shown in this diagram? Reply with the anatomical name only (2-5 words)."
                    }
                ]
            }]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"  Error calling vision model: {e}", file=sys.stderr)
        return None


def fuzzy_match(ground_truth: str, response: str) -> bool:
    """
    Check if all words in ground_truth appear in response (case-insensitive).

    Example:
      ground_truth = "brachial plexus"
      response = "The brachial plexus is shown in this diagram"
      → True (both "brachial" and "plexus" are in response)
    """
    if not response:
        return False

    gt_words = set(ground_truth.lower().split())
    resp_words = set(response.lower().split())

    return gt_words.issubset(resp_words)


def main():
    parser = argparse.ArgumentParser(description="Multimodal blind-test evaluation")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API calls")
    args = parser.parse_args()

    print("=" * 80)
    print("MULTIMODAL BLIND-TEST EVALUATION")
    print("=" * 80)
    print()

    # Get PNG files
    png_files = get_anatomy_png_files()
    print(f"Found {len(png_files)} PNG diagrams in public/anatomy/")
    print()

    if not png_files:
        print("ERROR: No PNG files found in public/anatomy/")
        sys.exit(1)

    # Dry-run preview
    if args.dry_run:
        print("DRY-RUN MODE: Preview of what would be evaluated")
        print("-" * 80)
        for i, (label, path) in enumerate(png_files.items(), 1):
            print(f"{i:2d}. Ground truth: '{label}'")
            print(f"    File: {Path(path).name}")
        print()
        print(f"Total diagrams to evaluate: {len(png_files)}")
        print("To run full evaluation: python eval/multimodal_eval.py")
        return

    # Full evaluation
    results = []
    exact_match_count = 0
    fuzzy_match_count = 0

    print("Evaluating diagrams...")
    print("-" * 80)

    for i, (ground_truth, image_path) in enumerate(png_files.items(), 1):
        print(f"\n[{i}/{len(png_files)}] Ground truth: '{ground_truth}'")

        # Load and encode image
        try:
            base64_data = image_to_base64(image_path)
        except Exception as e:
            print(f"  ERROR: Could not read image: {e}")
            results.append({
                "diagram": Path(image_path).name,
                "ground_truth": ground_truth,
                "response": None,
                "exact_match": False,
                "fuzzy_match": False,
                "error": str(e)
            })
            continue

        # Call vision model
        response = call_vision_model(image_path, base64_data)

        if response is None:
            print(f"  ERROR: Vision model call failed")
            results.append({
                "diagram": Path(image_path).name,
                "ground_truth": ground_truth,
                "response": None,
                "exact_match": False,
                "fuzzy_match": False,
                "error": "Vision model call failed"
            })
            continue

        print(f"  Response: '{response}'")

        # Evaluate: exact match
        exact = response.lower().strip() == ground_truth.lower().strip()

        # Evaluate: fuzzy match (all ground truth words in response)
        fuzzy = fuzzy_match(ground_truth, response)

        if exact:
            exact_match_count += 1
            print(f"  ✓ Exact match")

        if fuzzy:
            fuzzy_match_count += 1
            print(f"  ✓ Fuzzy match (all words present)")

        if not exact and not fuzzy:
            print(f"  ✗ No match")

        results.append({
            "diagram": Path(image_path).name,
            "ground_truth": ground_truth,
            "response": response,
            "exact_match": exact,
            "fuzzy_match": fuzzy
        })

    # Compute summary statistics
    total = len(results)
    exact_accuracy = (exact_match_count / total * 100) if total > 0 else 0
    fuzzy_accuracy = (fuzzy_match_count / total * 100) if total > 0 else 0

    print()
    print("=" * 80)
    print("EVALUATION RESULTS")
    print("=" * 80)
    print()
    print(f"Total diagrams evaluated: {total}")
    print(f"Exact match accuracy: {exact_match_count}/{total} ({exact_accuracy:.1f}%)")
    print(f"Fuzzy match accuracy: {fuzzy_match_count}/{total} ({fuzzy_accuracy:.1f}%)")
    print()

    # Save detailed results
    output_file = Path(__file__).parent / "metrics" / "multimodal_eval_results.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        f.write("# Multimodal Blind-Test Evaluation Results\n\n")
        f.write(f"**Date:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Model:** Claude Opus (anthropic/claude-opus-4)\n\n")
        f.write(f"**Prompt:** \"What anatomical structure is shown in this diagram? Reply with the anatomical name only (2-5 words).\"\n\n")
        f.write(f"## Summary Statistics\n\n")
        f.write(f"- **Total diagrams:** {total}\n")
        f.write(f"- **Exact match accuracy:** {exact_match_count}/{total} ({exact_accuracy:.1f}%)\n")
        f.write(f"- **Fuzzy match accuracy (words present):** {fuzzy_match_count}/{total} ({fuzzy_accuracy:.1f}%)\n\n")

        f.write(f"## Per-Diagram Results\n\n")
        f.write("| # | Diagram | Ground Truth | Response | Exact Match | Fuzzy Match | Notes |\n")
        f.write("|---|---------|--------------|----------|-------------|-------------|-------|\n")

        for i, result in enumerate(results, 1):
            diagram = result["diagram"]
            gt = result["ground_truth"]
            resp = result["response"] or "(error)"
            exact = "✓" if result.get("exact_match") else "✗"
            fuzzy = "✓" if result.get("fuzzy_match") else "✗"
            error_note = f" Error: {result.get('error')}" if result.get("error") else ""

            f.write(f"| {i} | {diagram} | {gt} | {resp} | {exact} | {fuzzy} |{error_note}|\n")

        f.write(f"\n## Interpretation\n\n")
        f.write(f"- **Exact Match:** Model response exactly matches the ground truth label (case-insensitive).\n")
        f.write(f"- **Fuzzy Match:** All words in the ground truth label appear in the model response (word-level recall).\n")
        f.write(f"- Fuzzy match is more lenient and captures cases where the model provides additional context but includes the correct concept name.\n\n")
        f.write(f"## Conclusions\n\n")
        f.write(f"The vision model achieved:\n")
        f.write(f"- {exact_accuracy:.1f}% exact match accuracy on blind anatomical structure identification\n")
        f.write(f"- {fuzzy_accuracy:.1f}% fuzzy match accuracy (concept words present in response)\n")
        f.write(f"\nThis demonstrates the multimodal capability of the system to recognize anatomical diagrams without text labels.\n")

    print(f"Results saved to: {output_file}")
    print()


if __name__ == "__main__":
    main()

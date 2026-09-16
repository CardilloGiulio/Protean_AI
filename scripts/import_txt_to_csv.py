import csv
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
CONTEXT_DIR = PROJECT_DIR / "src" / "protean_workspace" / "data" / "context"
FIELDNAMES = [
    "module",
    "topic",
    "concept",
    "definition",
    "must_know",
    "example",
    "security_note",
    "command",
    "common_mistake",
]


def main() -> None:
    raw_path = CONTEXT_DIR / "raw_knowledge.txt"
    out_path = CONTEXT_DIR / "knowledge.csv"

    if not raw_path.exists():
        raise SystemExit(f"Input file not found: {raw_path}")

    current_module = ""
    current_topic = ""
    rows: list[dict[str, str]] = []

    for line in raw_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()

        if stripped.startswith("MODULE "):
            current_module = stripped.removeprefix("MODULE ")
            continue

        if stripped.startswith("TOPIC "):
            current_topic = stripped
            continue

        if stripped.startswith("- ") and current_topic:
            definition = stripped.removeprefix("- ")
            rows.append(
                {
                    "module": current_module,
                    "topic": current_topic,
                    "concept": definition[:80],
                    "definition": definition,
                    "must_know": "",
                    "example": "",
                    "security_note": "",
                    "command": "",
                    "common_mistake": "",
                }
            )

    if not rows:
        raise SystemExit("No rows extracted.")

    with out_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")


if __name__ == "__main__":
    main()

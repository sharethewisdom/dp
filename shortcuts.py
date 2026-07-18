from __future__ import annotations

import json
import sys
import subprocess
from configparser import ConfigParser
from pathlib import Path
from typing import Any
from typing import TypedDict
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime

class VariableData(TypedDict):
    labels: list[str]
    values: list[str]
    multi_select: str
    separator: str

INI_ENCODING = "utf-16"

def read_config(file: Path) -> ConfigParser:
    """Read an INI configuration file."""
    if not file.is_file() or file.suffix.lower() != ".ini":
        raise SystemExit(f"Error: {file} is not an ini file")

    config = ConfigParser()
    config.optionxform = str  # preserve case

    with file.open("r", encoding=INI_ENCODING) as f:
        config.read_string(f.read())

    return config


def get_articles(config_file: Path) -> list[str]:
    """Collect all article IDs from the configuration."""
    config = read_config(config_file)

    articles: list[str] = []

    for section in config.sections():
        if config.has_option(section, "articles"):
            articles.extend(
                article.strip()
                for article in config.get(section, "articles").split(",")
            )

    return articles


def update_json(json_file: Path, articles: list[str]) -> None:
    """Update the JSON file with the article list."""
    if not json_file.is_file() or json_file.suffix.lower() != ".json":
        raise SystemExit(f"Error: {json_file} is not a json file")

    new_json: VariableData = {
        "labels": articles,
        "values": articles,
        "multi_select": "false",
        "separator": ",",
    }

    with json_file.open("r+", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

        data["variables"][0]["data"] = json.dumps(new_json)

        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

def make_zip(json_file: Path, zip_file: Path) -> None:
    with ZipFile(zip_file, "w", ZIP_DEFLATED) as zf:
        zf.write(json_file, arcname=json_file.name)

def publish(json_file: Path, zip_file: Path) -> None:
    subprocess.run(["git", "add", str(json_file)], check=True)
    subprocess.run(["git", "commit", "-m", "Automatic update"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    tag = datetime.now().strftime("v%Y.%m.%d-%H%M")

    subprocess.run([
        "gh",
        "release",
        "create",
        tag,
        str(zip_file),
        "--title",
        tag,
        "--notes",
        "Automatic update",
    ], check=True)

def main() -> None:
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("python shortcuts.py <FILE>\n\tthis script updates shortcuts.json (or FILE) using articles from decors.ini")
            return
        else:
            json_file = Path(sys.argv[1])
    else:
        json_file = Path("shortcuts.json")
    zip_file = Path("shortcuts.zip")
    articles = get_articles(Path("decors.ini"))
    update_json(json_file, articles)
    make_zip(json_file, zip_file)
    publish(json_file, zip_file)

if __name__ == "__main__":
    main()

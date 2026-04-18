#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHAT_FILE = ROOT / "_chat.txt"
APP_DIR = ROOT / "app"
DATA_DIR = ROOT / "data"
MANUAL_DIR = ROOT / "manual_assets"
MANUAL_ASSIGNMENTS = MANUAL_DIR / "assignments.json"
CLASS_ROSTER = MANUAL_DIR / "class_roster.json"
DATA_JS = APP_DIR / "data.js"
DATA_JSON = DATA_DIR / "families.json"


MESSAGE_START_RE = re.compile(r"^\u200e?\[(\d{1,2}/\d{1,2}/\d{4}, [^\]]+)\] ([^:]+): (.*)$")
ATTACHMENT_RE = re.compile(r"<attached: ([^>]+)>")


@dataclass
class Message:
    timestamp: str
    sender: str
    text: str
    attachments: list[str]


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "item"


def clean_text(text: str) -> str:
    text = text.replace("\u200e", "")
    text = text.replace("\u202f", " ")
    text = text.replace("\xa0", " ")
    text = text.replace("‎", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_sender(sender: str) -> str:
    sender = clean_text(sender)
    sender = sender.replace("~ ", "").replace("~", "")
    return sender.strip()


def split_messages(raw: str) -> list[Message]:
    lines = raw.splitlines()
    messages: list[Message] = []
    current: list[str] = []

    for line in lines:
        if MESSAGE_START_RE.match(line):
            if current:
                msg = parse_message_block(current)
                if msg:
                    messages.append(msg)
            current = [line]
        else:
            if current:
                current.append(line)

    if current:
        msg = parse_message_block(current)
        if msg:
            messages.append(msg)

    return messages


def parse_message_block(lines: list[str]) -> Message | None:
    first = lines[0]
    match = MESSAGE_START_RE.match(first)
    if not match:
        return None

    timestamp, sender, first_text = match.groups()
    body = "\n".join([first_text, *lines[1:]])
    attachments = ATTACHMENT_RE.findall(body)
    text = ATTACHMENT_RE.sub("", body)
    return Message(
        timestamp=timestamp,
        sender=clean_sender(sender),
        text=clean_text(text),
        attachments=attachments,
    )


def looks_like_intro(message: Message) -> bool:
    text = message.text.lower()
    intro_markers = [
        "this is ",
        "here's our daughter",
        "here’s our daughter",
        "here's our son",
        "here’s our son",
        "we are ",
        "i'm ",
        "i’m ",
        "my husband is",
        "hubby",
        "(mum)",
        "(dad)",
    ]
    return any(marker in text for marker in intro_markers) and bool(message.attachments)


def extract_child_name(text: str) -> str | None:
    patterns = [
        r"\bthis is my sidekick,\s*([A-Z][a-zA-Z'’-]+)",
        r"\bthis is\s+([A-Z][a-zA-Z'’-]+)",
        r"\bhere['’]s our (?:daughter|son)\s+([A-Z][a-zA-Z'’-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return tidy_name(match.group(1))
    return None


def extract_parents(text: str) -> list[dict[str, str]]:
    parent_pairs: list[tuple[str, str | None]] = []
    patterns = [
        r"\bwe are\s+([A-Z][a-zA-Z'’-]+)\s*(?:and|&)\s*([A-Z][a-zA-Z'’-]+)",
        r"\bi['’]?m\s+([A-Z][a-zA-Z'’-]+)\s+and my husband is\s+([A-Z][a-zA-Z'’-]+)",
        r"\bi['’]?m\s+([A-Z][a-zA-Z'’-]+)\s+and my wife is\s+([A-Z][a-zA-Z'’-]+)",
        r"\bi['’]?m\s+([A-Z][a-zA-Z'’-]+)\s+and hubby\s*[-:]\s*([A-Z][a-zA-Z'’-]+)",
        r"\(mum\)\s*([A-Z][a-zA-Z'’-]+)\s*&\s*\(dad\)\s*([A-Z][a-zA-Z'’-]+)",
        r"[-–]\s*([A-Z][a-zA-Z'’-]+)\s*(?:and|&)\s*([A-Z][a-zA-Z'’-]+)\s*$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parent_pairs.append((tidy_name(match.group(1)), tidy_name(match.group(2))))
            break

    if not parent_pairs:
        return []

    first, second = parent_pairs[0]
    return [
        {"name": first, "role": "parent"},
        {"name": second, "role": "parent"},
    ]


def tidy_name(name: str) -> str:
    name = clean_text(name)
    name = re.sub(r"[^A-Za-z'’-]+$", "", name)
    if len(name) <= 3:
        return name.upper() if name.isupper() else name.title()
    return name[:1].upper() + name[1:]


def build_intro_family(message: Message) -> dict[str, Any] | None:
    child_name = extract_child_name(message.text)
    if not child_name:
        return None

    parents = extract_parents(message.text)
    family_id = slugify(child_name)

    family = {
        "id": family_id,
        "child": {
            "id": f"{family_id}-child",
            "name": child_name,
            "aliases": [],
            "profile_image": first_image(message.attachments),
        },
        "parents": [
            {
                "id": f"{family_id}-parent-{index + 1}",
                "name": parent["name"],
                "role": parent["role"],
                "profile_image": None,
            }
            for index, parent in enumerate(parents)
        ],
        "whatsapp_names": [message.sender],
        "notes": [],
        "background": {
            "languages": [],
            "country_or_region": [],
            "work_or_role": [],
            "memory_hints": [],
        },
        "tags": ["intro-post", "chat-extracted"],
        "status": "draft",
        "completeness": "partial",
        "galleries": {
            "child": [img for img in message.attachments if is_image(img)],
            "mother": [],
            "father": [],
            "parent": [],
            "family": [img for img in message.attachments if is_image(img)],
            "screenshots": [],
            "unknown": [],
        },
        "evidence": [
            {
                "timestamp": message.timestamp,
                "sender": message.sender,
                "text": message.text,
                "attachments": message.attachments,
                "confidence": "high" if parents else "medium",
            }
        ],
    }

    if "family" in message.text.lower():
        family["tags"].append("family-photo")
    if len(parents) == 2:
        family["status"] = "needs-parent-photos"

    return family


def is_image(filename: str) -> bool:
    return filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))


def first_image(attachments: list[str]) -> str | None:
    for attachment in attachments:
        if is_image(attachment):
            return attachment
    return None


def merge_duplicate_families(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}

    for family in families:
        existing = by_id.get(family["id"])
        if not existing:
            by_id[family["id"]] = family
            continue

        existing["whatsapp_names"] = sorted(set(existing["whatsapp_names"] + family["whatsapp_names"]))
        existing["tags"] = sorted(set(existing["tags"] + family["tags"]))
        for gallery_name, images in family["galleries"].items():
            merged = existing["galleries"].setdefault(gallery_name, [])
            existing["galleries"][gallery_name] = unique_list(merged + images)
        existing["evidence"].extend(family["evidence"])
        existing["evidence"].sort(key=lambda item: item["timestamp"])

        existing_parent_names = {parent["name"] for parent in existing["parents"]}
        for parent in family["parents"]:
            if parent["name"] not in existing_parent_names:
                parent["id"] = f"{existing['id']}-parent-{len(existing['parents']) + 1}"
                existing["parents"].append(parent)

        if not existing["child"]["profile_image"] and family["child"]["profile_image"]:
            existing["child"]["profile_image"] = family["child"]["profile_image"]

    return list(by_id.values())


def unique_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output


def infer_additional_hints(messages: list[Message], families: list[dict[str, Any]]) -> None:
    child_lookup = {family["child"]["name"].lower(): family for family in families}
    for message in messages:
        lowered = message.text.lower()
        for child_name, family in child_lookup.items():
            if child_name in lowered and not any(ev["timestamp"] == message.timestamp for ev in family["evidence"]):
                if any(keyword in lowered for keyword in ["birthday", "hat", "lunch", "invite", "love to join", "can't make"]):
                    family["background"]["memory_hints"].append(
                        f"{message.timestamp}: {message.text[:120]}"
                    )

    for family in families:
        family["background"]["memory_hints"] = unique_list(family["background"]["memory_hints"])


def build_manual_image_index() -> dict[str, list[dict[str, Any]]]:
    if not MANUAL_ASSIGNMENTS.exists():
        return {}
    data = json.loads(MANUAL_ASSIGNMENTS.read_text(encoding="utf-8"))
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in data.get("items", []):
        family_id = item.get("family_id")
        if family_id:
            index[family_id].append(item)
    return index


def load_class_roster() -> list[dict[str, Any]]:
    if not CLASS_ROSTER.exists():
        return []
    data = json.loads(CLASS_ROSTER.read_text(encoding="utf-8"))
    return data.get("families", [])


def normalize_match_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(text).lower())


def merge_class_roster(families: list[dict[str, Any]], roster: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {family["id"]: family for family in families}

    for item in roster:
        family_id = item["id"]
        existing = by_id.get(family_id)
        parent_names = item.get("parents", [])
        whatsapp_names = item.get("whatsapp_names", [])

        if existing:
            existing["child"]["name"] = item.get("child_name", existing["child"]["name"])
            existing["child"]["aliases"] = unique_list(existing["child"].get("aliases", []) + item.get("child_aliases", []))
            existing["whatsapp_names"] = unique_list(existing["whatsapp_names"] + whatsapp_names)

            existing["parents"] = [
                {
                    "id": f"{family_id}-parent-{index + 1}",
                    "name": parent_name,
                    "role": "parent",
                    "profile_image": existing["parents"][index]["profile_image"] if index < len(existing["parents"]) else None,
                }
                for index, parent_name in enumerate(parent_names)
            ]
            existing["tags"] = sorted(set(existing["tags"] + ["roster-confirmed"]))
            if item.get("note"):
                existing["notes"] = unique_list(existing["notes"] + [item["note"]])
            continue

        child_name = item.get("child_name", "Unknown child")
        new_family = {
            "id": family_id,
            "child": {
                "id": f"{family_id}-child",
                "name": child_name,
                "aliases": item.get("child_aliases", []),
                "profile_image": None,
            },
            "parents": [
                {
                    "id": f"{family_id}-parent-{index + 1}",
                    "name": parent_name,
                    "role": "parent",
                    "profile_image": None,
                }
                for index, parent_name in enumerate(parent_names)
            ],
            "whatsapp_names": whatsapp_names,
            "notes": [item["note"]] if item.get("note") else [],
            "background": {
                "languages": [],
                "country_or_region": [],
                "work_or_role": [],
                "memory_hints": [],
            },
            "tags": ["roster-confirmed"],
            "status": "draft",
            "completeness": "sparse",
            "galleries": {
                "child": [],
                "mother": [],
                "father": [],
                "parent": [],
                "family": [],
                "screenshots": [],
                "unknown": [],
            },
            "evidence": [],
        }
        by_id[family_id] = new_family

    return list(by_id.values())


def apply_manual_parent_avatars(families: list[dict[str, Any]], roster: list[dict[str, Any]]) -> None:
    roster_by_id = {item["id"]: item for item in roster}
    avatar_files = [
        path
        for path in MANUAL_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]

    for family in families:
        roster_item = roster_by_id.get(family["id"])
        if not roster_item:
            continue

        whatsapp_names = roster_item.get("whatsapp_names", [])
        parent_names = roster_item.get("parents", [])

        match_targets: list[tuple[int, str]] = []
        for index, parent_name in enumerate(parent_names):
            match_targets.append((index, parent_name))
        for index, whatsapp_name in enumerate(whatsapp_names):
            if index < len(parent_names):
                match_targets.append((index, whatsapp_name))

        target_map: dict[str, int] = {}
        for index, label in match_targets:
            target_map[normalize_match_key(label)] = index

        if len(whatsapp_names) == 1 and parent_names:
            target_map[normalize_match_key(whatsapp_names[0])] = 0

        for avatar_file in avatar_files:
            stem_key = normalize_match_key(avatar_file.stem)
            if stem_key not in target_map:
                continue
            parent_index = target_map[stem_key]
            if parent_index >= len(family["parents"]):
                continue
            family["parents"][parent_index]["profile_image"] = f"manual_assets/{avatar_file.name}"
            if parent_index == 0:
                family["galleries"]["mother"] = unique_list(family["galleries"].get("mother", []) + [f"manual_assets/{avatar_file.name}"])
            elif parent_index == 1:
                family["galleries"]["father"] = unique_list(family["galleries"].get("father", []) + [f"manual_assets/{avatar_file.name}"])
            else:
                family["galleries"]["parent"] = unique_list(family["galleries"].get("parent", []) + [f"manual_assets/{avatar_file.name}"])
            family["tags"] = sorted(set(family["tags"] + ["manual-parent-avatar"]))


def apply_manual_assignments(families: list[dict[str, Any]], manual_index: dict[str, list[dict[str, Any]]]) -> None:
    for family in families:
        for item in manual_index.get(family["id"], []):
            category = item.get("category", "unknown")
            image_path = item.get("file")
            if image_path:
                family["galleries"].setdefault(category, [])
                family["galleries"][category] = unique_list(family["galleries"][category] + [image_path])
            if item.get("note"):
                family["notes"].append(item["note"])
            if item.get("tag"):
                family["tags"].append(item["tag"])

        family["notes"] = unique_list(family["notes"])
        family["tags"] = sorted(set(family["tags"]))


def build_unassigned_media(all_files: list[str], families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assigned = set()
    for family in families:
        for gallery in family["galleries"].values():
            assigned.update(gallery)
        for evidence in family["evidence"]:
            assigned.update(evidence["attachments"])

    unassigned: list[dict[str, Any]] = []
    for file_name in all_files:
        if file_name in assigned:
            continue
        lower = file_name.lower()
        media_type = "screenshot" if lower.endswith(".png") and "screenshot" in lower else "photo"
        if lower.endswith(".mp4"):
            media_type = "video"
        unassigned.append(
            {
                "file": file_name,
                "type": media_type,
                "source": "workspace",
            }
        )
    return sorted(unassigned, key=lambda item: item["file"].lower())


def compute_completeness(family: dict[str, Any]) -> None:
    has_child = bool(family["child"]["profile_image"])
    has_two_parents = len(family["parents"]) >= 2
    has_parent_photo = any(family["galleries"].get(category) for category in ("mother", "father", "parent"))
    if has_child and has_two_parents and has_parent_photo:
        family["completeness"] = "rich"
    elif has_child and has_two_parents:
        family["completeness"] = "partial"
    else:
        family["completeness"] = "sparse"


def serialize_dataset(families: list[dict[str, Any]], unassigned_media: list[dict[str, Any]], messages: list[Message]) -> dict[str, Any]:
    summary = {
        "family_count": len(families),
        "unassigned_media_count": len(unassigned_media),
        "message_count": len(messages),
    }
    return {
        "summary": summary,
        "families": families,
        "unassigned_media": unassigned_media,
    }


def main() -> None:
    APP_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    MANUAL_DIR.mkdir(exist_ok=True)

    raw_chat = CHAT_FILE.read_text(encoding="utf-8")
    messages = split_messages(raw_chat)
    intro_families = [build_intro_family(message) for message in messages if looks_like_intro(message)]
    families = merge_duplicate_families([family for family in intro_families if family])
    roster = load_class_roster()
    families = merge_class_roster(families, roster)
    infer_additional_hints(messages, families)
    apply_manual_assignments(families, build_manual_image_index())
    apply_manual_parent_avatars(families, roster)

    workspace_media = sorted(
        [
            path.name
            for path in ROOT.iterdir()
            if path.is_file() and path.name != CHAT_FILE.name and not path.name.startswith(".")
        ]
    )
    unassigned_media = build_unassigned_media(workspace_media, families)

    for family in families:
        compute_completeness(family)

    families.sort(key=lambda item: item["child"]["name"].lower())
    dataset = serialize_dataset(families, unassigned_media, messages)

    DATA_JSON.write_text(json.dumps(dataset, indent=2, ensure_ascii=False), encoding="utf-8")
    DATA_JS.write_text(
        "window.APP_DATA = " + json.dumps(dataset, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    if not MANUAL_ASSIGNMENTS.exists():
        MANUAL_ASSIGNMENTS.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "family_id": "eli",
                            "file": "manual_assets/example-parent-photo.jpg",
                            "category": "mother",
                            "note": "Example only: drop your own files into manual_assets and update this file.",
                            "tag": "manual-photo",
                        }
                    ]
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    print(f"Built {len(families)} families and {len(unassigned_media)} unassigned media items.")


if __name__ == "__main__":
    main()

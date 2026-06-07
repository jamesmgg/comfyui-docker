#!/usr/bin/env python3
"""Build the Wan 2.2 T2V 500 prompt manifest."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "batch" / "wan22_t2v_manifest.json"

CATEGORIES = [
    ("cyberpunk-dystopian", "Cyberpunk Dystopian", 72),
    ("high-fantasy-magic", "High Fantasy Magic", 72),
    ("cinematic-horror-thriller", "Cinematic Horror Thriller", 72),
    ("historical-period-epics", "Historical Period Epics", 72),
    ("space-sci-fi-exploration", "Space Sci-Fi Exploration", 72),
    ("architecture-fly-throughs", "Architecture Fly-Throughs", 70),
    ("post-apocalyptic-wasteland", "Post-Apocalyptic Wasteland", 70),
]

PROMPT_255 = "Fly-through of a neon-lit narrow Tokyo alleyway. Camera first-person view. Night rain."

BANKS = {
    "cyberpunk-dystopian": {
        "subjects": [
            "neon street vendor", "rain-soaked courier", "hologram repair crew", "masked noodle chef",
            "rooftop drone mechanic", "augmented detective", "underground synth band", "black-market medic",
            "corporate tower protest", "subway platform hacker", "servo-limbed dancer", "android florist",
        ],
        "places": [
            "under elevated maglev tracks", "beside a steam vent market", "inside a flooded arcade",
            "on a billboard-lit skybridge", "in a security checkpoint queue", "at a midnight food stall",
        ],
    },
    "high-fantasy-magic": {
        "subjects": [
            "crystal antlered stag", "runed tower gate", "moonlit elven envoy", "dragon hatchery keeper",
            "floating island caravan", "enchanted blacksmith", "spellbound forest shrine", "storm mage duel",
            "ancient library spirit", "glowing river oracle", "wyvern rider patrol", "fae lantern parade",
        ],
        "places": [
            "beneath giant silver trees", "across a misty mountain pass", "inside a candlelit citadel",
            "over a luminous mushroom valley", "beside a ruined stone circle", "through a snow-bright fortress",
        ],
    },
    "cinematic-horror-thriller": {
        "subjects": [
            "abandoned motel hallway", "silent figure at the pier", "flickering hospital ward", "foggy cornfield chase",
            "old house attic door", "subway tunnel flashlight", "storm cellar discovery", "empty carnival ride",
            "mirror in a dark apartment", "forest road breakdown", "security camera room", "seaside lighthouse stairs",
        ],
        "places": [
            "during a power outage", "under pulsing emergency lights", "as rain lashes the windows",
            "with breath visible in cold air", "while distant sirens fade", "in a slow creeping fog",
        ],
    },
    "historical-period-epics": {
        "subjects": [
            "Roman legion crossing", "samurai messenger arrival", "Viking ship landing", "Renaissance painter studio",
            "Mughal garden procession", "medieval siege tower", "Victorian train platform", "ancient market square",
            "Ottoman palace courtyard", "frontier wagon camp", "Tang dynasty lantern street", "Napoleonic cavalry scout",
        ],
        "places": [
            "at dawn with low mist", "beneath banners in the wind", "through a crowded stone street",
            "beside torchlit city walls", "under a dramatic storm sky", "in warm late afternoon sun",
        ],
    },
    "space-sci-fi-exploration": {
        "subjects": [
            "orbital repair astronaut", "ice moon rover convoy", "first contact observation deck", "asteroid mining elevator",
            "generation ship garden", "Mars dust storm shelter", "alien archive chamber", "deep space telescope array",
            "terraforming drone swarm", "lunar cargo port", "cryosleep bay awakening", "solar sail deployment",
        ],
        "places": [
            "with stars sharp through glass", "above a planet's bright limb", "inside a humming airlock",
            "across a cratered horizon", "under blue instrument light", "beside floating dust particles",
        ],
    },
    "architecture-fly-throughs": {
        "subjects": [
            "brutalist museum atrium", "parametric glass airport", "desert modern villa", "tropical concrete library",
            "underground transit hall", "cliffside spa complex", "timber concert hall", "futurist train terminal",
            "minimalist chapel interior", "Art Deco hotel lobby", "folded steel gallery", "courtyard school campus",
        ],
        "places": [
            "with a continuous dolly forward", "gliding through layered arches", "rising from floor to skylight",
            "tracking along reflective stone", "passing through warm interior shadows", "with morning light shafts",
        ],
    },
    "post-apocalyptic-wasteland": {
        "subjects": [
            "solar scavenger convoy", "overgrown freeway camp", "rusted robot shepherd", "desert water trader",
            "abandoned mall greenhouse", "radio tower lookout", "dust storm motorcycle patrol", "sunken suburb canoe",
            "rail yard settlement", "masked mechanic workshop", "cracked dam crossing", "wind farm refuge",
        ],
        "places": [
            "under a bleached sky", "as ash drifts sideways", "with plants reclaiming concrete",
            "beside torn warning signs", "through heat shimmer", "in orange sunset haze",
        ],
    },
}

CAMERA = [
    "slow dolly forward", "gentle handheld drift", "low tracking shot", "smooth crane rise",
    "first-person glide", "wide cinematic push-in", "orbiting reveal", "steady lateral pan",
]
LIGHTING = [
    "moody high-contrast lighting", "soft volumetric light", "rainy reflective highlights",
    "golden rim light", "cold blue practical light", "naturalistic cinematic lighting",
]


def slug(text: str, words: int = 3) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    parts = [part for part in value.split("-") if part]
    return "-".join(parts[:words]) or "prompt"


def original_prompt(prompt_id: int, category_slug: str, local_index: int) -> str:
    if prompt_id == 255:
        return PROMPT_255
    bank = BANKS[category_slug]
    subject = bank["subjects"][local_index % len(bank["subjects"])]
    place = bank["places"][(local_index // len(bank["subjects"])) % len(bank["places"])]
    camera = CAMERA[(prompt_id + local_index) % len(CAMERA)]
    return f"{subject.title()} {place}. Camera: {camera}. 5 second cinematic video."


def expanded_prompt(original: str, category_name: str, prompt_id: int) -> str:
    camera = CAMERA[prompt_id % len(CAMERA)]
    lighting = LIGHTING[prompt_id % len(LIGHTING)]
    return (
        f"{original} {category_name} style. Concrete foreground subject detail, layered midground and background "
        f"depth, {camera} camera behavior, visible environmental motion, and {lighting}. Keep identities, objects, "
        "and spatial layout temporally consistent from first frame to last. Smooth natural motion, cinematic "
        "composition, realistic texture detail."
    )


def build_manifest() -> list[dict]:
    items: list[dict] = []
    prompt_id = 1
    for category_slug, category_name, count in CATEGORIES:
        for local_index in range(count):
            original = original_prompt(prompt_id, category_slug, local_index)
            item_category_slug = category_slug
            item_category_name = category_name
            if prompt_id == 255:
                item_category_slug = "cyberpunk-dystopian"
                item_category_name = "Cyberpunk Dystopian"
            short_slug = slug(original)
            prefix = f"wan-t2v-batch/{item_category_slug}/{prompt_id:03d}-{short_slug}"
            items.append(
                {
                    "id": f"{prompt_id:03d}",
                    "category": item_category_slug,
                    "original_prompt": original,
                    "expanded_prompt": expanded_prompt(original, item_category_name, prompt_id),
                    "status": "pending",
                    "assigned_port": None,
                    "prompt_id": None,
                    "output_subfolder": f"wan-t2v-batch/{item_category_slug}",
                    "filename_prefix": prefix,
                    "output_file": None,
                    "runtime_seconds": None,
                    "verified": False,
                }
            )
            prompt_id += 1
    return items


def main() -> int:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build_manifest(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

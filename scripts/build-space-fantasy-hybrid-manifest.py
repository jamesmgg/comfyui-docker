#!/usr/bin/env python3
"""Build 500 space/fantasy/futuristic hybrid-style prompts."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "batch" / "space_fantasy_hybrid_highstep_manifest.json"
OUTPUT_PREFIX = "space-fantasy-hybrid-highstep"

CATEGORIES = [
    ("cosmic-frontiers", "Cosmic Frontiers"),
    ("enchanted-star-realms", "Enchanted Star Realms"),
    ("futuristic-city-life", "Futuristic City Life"),
    ("alien-wilderness", "Alien Wilderness"),
    ("mythic-space-voyages", "Mythic Space Voyages"),
    ("celestial-creatures", "Celestial Creatures"),
    ("arcane-technology", "Arcane Technology"),
    ("orbital-fantasy-kingdoms", "Orbital Fantasy Kingdoms"),
    ("retrofuture-adventurers", "Retrofuture Adventurers"),
    ("cosmic-architecture", "Cosmic Architecture"),
]

SUBJECTS = {
    "cosmic-frontiers": [
        "young navigator on a glass-domed rover", "asteroid prospector with a glowing map", "survey pilot beside a silver lander",
        "botanist tending crystal crops", "frontier mechanic under twin moons", "child explorer releasing beacon kites",
        "starport courier crossing a dust plain", "geologist scanning a floating boulder", "family caravan near a crater oasis",
        "robot mule carrying luminous supplies",
    ],
    "enchanted-star-realms": [
        "moon sorcerer opening a comet gate", "elf astronomer reading a living star chart", "witch queen beside a nebula fountain",
        "apprentice mage polishing a tiny planet", "griffin rider above a ringed moon", "wizard gardener pruning solar vines",
        "starlight bard playing a crystal harp", "oracle child holding a pocket eclipse", "knight guarding a constellation bridge",
        "fairy cartographer painting meteor trails",
    ],
    "futuristic-city-life": [
        "hover-bike baker delivering breakfast", "neon tailor fitting a levitating coat", "street musician with a hologram cello",
        "school kids boarding an air tram", "market chef tossing noodles over blue flame", "window washer drone beside a tower",
        "raincoat detective at a skywalk crossing", "gardener maintaining rooftop algae ponds", "courier skating through glass tunnels",
        "elderly chess player with robot spectators",
    ],
    "alien-wilderness": [
        "traveler crossing a lavender moss desert", "researcher hiding under giant translucent leaves", "scout canoeing a mercury river",
        "climber beside floating basalt columns", "wildlife painter near spiral-horned grazers", "astronaut walking through glowing spores",
        "nomad camp under umbrella mushrooms", "ranger tracking footprints in blue sand", "child feeding a gentle six-eyed creature",
        "survival tent beside a singing ice cliff",
    ],
    "mythic-space-voyages": [
        "dragon-prowed starship leaving harbor", "captain holding a compass made of fire", "crew raising sails of solar silk",
        "mermaid pilot guiding a comet skiff", "dwarf engineer stoking an antimatter forge", "phoenix figurehead lighting the route",
        "sky monk meditating in the observation bay", "pirate princess steering through an asteroid reef", "giant turtle ship crossing auroras",
        "mapmaker tracing a path through dark matter",
    ],
    "celestial-creatures": [
        "baby moon whale drifting over rooftops", "crystal fox leaping between comets", "star lion resting in an observatory",
        "tiny dragon curled around a satellite dish", "owl made of nebula dust turning its head", "horse with meteor mane running free",
        "jellyfish constellation pulsing above water", "cat with galaxy eyes on a control panel", "butterfly swarm orbiting a prism tree",
        "gentle stone giant carrying a sunrise",
    ],
    "arcane-technology": [
        "engineer enchanting a levitation engine", "mage soldering runes onto a circuit board", "robot familiar brewing blue potions",
        "blacksmith forging a plasma staff", "alchemist calibrating a quantum cauldron", "inventor testing a spell-powered jetpack",
        "librarian awakening a mechanical spellbook", "technician aligning crystal processors", "pilot charging a rune battery",
        "clockwork assistant painting sigils in air",
    ],
    "orbital-fantasy-kingdoms": [
        "princess greeting ships at a castle airlock", "royal guard patrolling a moonlit docking ring", "market square floating above a planet",
        "king's messenger riding a winged scooter", "feast hall with windows facing Saturn-like rings", "blacksmith shop on a rotating citadel",
        "children playing beside a gravity fountain", "queen planting a flag in an orbital garden", "bard performing on a balcony in space",
        "armored librarian guarding a star archive",
    ],
    "retrofuture-adventurers": [
        "helmeted explorer holding a ray compass", "pulp heroine jumping from a chrome rocket", "teen mechanic repairing a bubble car",
        "space ranger waving from a diner booth", "scientist unpacking brass instruments", "detective entering a rocket motel",
        "pilot leaning on a finned spacecraft", "kid sidekick carrying a lunchbox transmitter", "radio operator tracking a mystery signal",
        "expedition cook serving soup in low gravity",
    ],
    "cosmic-architecture": [
        "cathedral grown from white meteor stone", "library spiraling around a miniature sun", "glass palace suspended above a moon crater",
        "train station inside a hollow asteroid", "botanical dome overlooking a gas giant", "temple bridge crossing a star river",
        "cliffside observatory with golden ramps", "floating amphitheater under aurora curtains", "museum carved into an ice comet",
        "quiet apartment tower with orbital gardens",
    ],
}

SETTINGS = [
    "beneath a violet ringed planet", "inside a luminous cloud city", "on a moonlit launch terrace",
    "beside a turquoise crater lake", "through a market of floating lanterns", "under slow-moving auroras",
    "near a silver forest of antenna trees", "inside a rain-slick transit arcade", "above a glowing canyon",
    "at dawn as three suns rise",
]

ACTIONS = [
    "dust and tiny sparks drifting through the foreground", "fabric, hair, and small props moving naturally",
    "background characters crossing at different depths", "soft atmospheric particles catching the light",
    "reflections sliding across polished surfaces", "small creatures reacting to the camera movement",
    "distant vehicles gliding through the sky", "mist and light beams changing as the shot advances",
    "hands and faces staying consistent during motion", "environmental details moving with gentle parallax",
]

CAMERAS = [
    "slow dolly forward", "smooth crane rise", "gentle handheld drift", "wide cinematic push-in",
    "low tracking shot", "orbiting reveal", "first-person glide", "steady lateral pan",
    "slow tilt from foreground to skyline", "soft over-the-shoulder follow",
]

LIGHTING = [
    "soft volumetric starlight", "warm sunrise rim light", "cool moonlit reflections",
    "glowing practical lights", "golden fantasy backlight", "clean animated-feature lighting",
    "photoreal atmospheric haze", "colorful nebula bounce light", "rainy reflective highlights",
    "gentle high-contrast cinematic light",
]


def slug(text: str, words: int = 4) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return "-".join([part for part in value.split("-") if part][:words]) or "prompt"


def build_manifest() -> list[dict]:
    items: list[dict] = []
    prompt_id = 1
    for category_slug, category_name in CATEGORIES:
        subjects = SUBJECTS[category_slug]
        for local_index in range(50):
            subject = subjects[local_index % len(subjects)]
            setting = SETTINGS[(local_index // len(subjects) + prompt_id) % len(SETTINGS)]
            camera = CAMERAS[(prompt_id + local_index) % len(CAMERAS)]
            lighting = LIGHTING[(prompt_id * 2 + local_index) % len(LIGHTING)]
            action = ACTIONS[(prompt_id + local_index * 3) % len(ACTIONS)]
            original = f"{subject.title()} {setting}. Camera: {camera}. Five-second cinematic video."
            action_sentence = action[0].upper() + action[1:]
            expanded = (
                f"{original} {category_name} scene. Hybrid visual style combining expressive animated feature-film "
                f"shapes with photoreal materials, natural depth, and {lighting}. {action_sentence}. Layered foreground, "
                "midground, and background composition with coherent scale and spatial continuity. Smooth natural "
                "motion, consistent identities and objects, rich color, tactile surfaces, and polished cinematic framing."
            )
            prefix = f"{OUTPUT_PREFIX}/{category_slug}/{prompt_id:03d}-{slug(original)}"
            items.append(
                {
                    "id": f"{prompt_id:03d}",
                    "category": category_slug,
                    "original_prompt": original,
                    "expanded_prompt": expanded,
                    "status": "pending",
                    "assigned_port": None,
                    "prompt_id": None,
                    "output_subfolder": f"{OUTPUT_PREFIX}/{category_slug}",
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

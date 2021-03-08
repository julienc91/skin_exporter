# -*- coding: utf-8 -*-

import json
from enum import IntEnum
from typing import Generator

import vdf
from pathlib import Path


# config
game_path = Path(
    "/home/julien/.local/share/Steam/steamapps/common/Counter-Strike Global Offensive/"
)
languages = ["english", "french"]
# end config


class ItemTypes(IntEnum):
    weapon_skin = 1
    player_skin = 2
    glove_skin = 3
    knive_skin = 4
    sticker = 5


def load_vdf(path: Path, **kwargs) -> dict:
    with open(path, **kwargs) as f:
        return vdf.parse(f)


def load_items_game_cdn(path: Path) -> list:
    with open(path) as f:
        return [line.split("=")[0] for line in f]


def parse_translation_key(key: str) -> str:
    return key.lstrip("#").lower()


def parse_collections(collections: list[dict]) -> Generator[dict, None, None]:
    for collection in collections:
        assert collection["is_collection"] == "1"
        collection_name_key = parse_translation_key(collection["name"])
        collection_description_key = parse_translation_key(
            collection["set_description"]
        )
        for res in parse_collection_items(collection["items"]):
            res["collection"] = {
                "name_key": collection_name_key,
                "description_key": collection_description_key,
            }
            yield res


def parse_collection_items(items: list[str]) -> Generator[dict, None, None]:
    for item in items:
        try:
            res = {
                "type": ItemTypes.weapon_skin,
                "paint_kit": item[1:].split("]")[0],
                "weapon": {"id": item.split("]")[1]},
            }
        except IndexError:
            # player models
            continue
        yield res


def parse_gloves(items: dict) -> Generator[dict, None, None]:
    gloves_id_to_paintkit_prefixes = {
        "studded_brokenfang_gloves": "operation10",
        "studded_hydra_gloves": "bloodhound_hydra",
        "studded_bloodhound_gloves": "bloodhound",
        "leather_handwraps": "handwrap",
        "motorcycle_gloves": "motorcycle",
        "slick_gloves": "slick",
        "specialist_gloves": "specialist",
        "sporty_gloves": "sporty",
    }
    expected_rarity = "ancient"
    for name, rarity in items.items():
        if rarity != expected_rarity:
            continue
        for glove_id, prefix in gloves_id_to_paintkit_prefixes.items():
            if not name.startswith(prefix + "_"):
                continue
            yield {
                "type": ItemTypes.glove_skin,
                "weapon": {
                    "id": glove_id,
                },
                "paint_kit": name,
            }
            break


def parse_knives(items: list) -> Generator[dict, None, None]:
    knives_prefixes = {
        "weapon_bayonet",
        "weapon_knife_butterfly",
        "weapon_knife_canis",
        "weapon_knife_cord",
        "weapon_knife_css",
        "weapon_knife_falchion",
        "weapon_knife_flip",
        "weapon_knife_gut",
        "weapon_knife_gypsy_jackknife",
        "weapon_knife_karambit",
        "weapon_knife_m9_bayonet",
        "weapon_knife_outdoor",
        "weapon_knife_push",
        "weapon_knife_skeleton",
        "weapon_knife_stiletto",
        "weapon_knife_survival_bowie",
        "weapon_knife_tactical",
        "weapon_knife_ursus",
        "weapon_knife_widowmaker",
    }
    for item in items:
        for knife_id in knives_prefixes:
            if not item.startswith(knife_id + "_"):
                continue
            yield {
                "type": ItemTypes.knive_skin,
                "weapon": {"id": knife_id},
                "paint_kit": item[len(knife_id) + 1 :],
            }


def fill_paintkit(item: dict, paint_kits: list[dict]):
    for paint_kit in paint_kits:
        if paint_kit["name"] == item["paint_kit"]:
            item["name_key"] = parse_translation_key(paint_kit["description_tag"])
            item["description_key"] = parse_translation_key(
                paint_kit["description_string"]
            )

            item["min_wear"] = float(paint_kit.get("wear_remap_min", 0.0))
            item["max_wear"] = float(paint_kit.get("wear_remap_max", 1.0))
            item["pattern"] = paint_kit.get("pattern")
            item["vmt"] = paint_kit.get("vmt_path")

            if item["type"] == ItemTypes.weapon_skin:
                item["style"] = paint_kit["style"]
            return
    raise ValueError(f"No paintkit found with name {item['paint_kit']}")


def fill_prefabs(item: dict, prefabs: dict):
    weapon_prefab = item["weapon"]["id"] + "_prefab"
    prefab = prefabs[weapon_prefab]
    item["weapon"]["name_key"] = parse_translation_key(prefab["item_name"])
    item["weapon"]["description_key"] = parse_translation_key(
        prefab["item_description"]
    )


def fill_rarity(item: dict, paint_kits_rarity: dict):
    paint_kit = item["paint_kit"]
    rarity = paint_kits_rarity[paint_kit]
    item["rarity"] = rarity


def fill_weapon_info(item: dict, items: list[dict]):
    for item_ in items:
        if item_["name"] == item["weapon"]["id"]:
            item["weapon"]["name_key"] = parse_translation_key(item_["item_name"])
            item["weapon"]["description_key"] = parse_translation_key(
                item_["item_description"]
            )
            return
    raise ValueError(f"No item found with name {item['weapon']['id']}")


def fill_glove_prefab(item: dict, items: list[dict]):
    fill_weapon_info(item, items)


def fill_knife_prefab(item: dict, items: list[dict]):
    fill_weapon_info(item, items)


def fill_translations(item: dict, translations: dict):
    item.setdefault("name", {})
    item.setdefault("description", {})
    if item.get("collection"):
        item["collection"].setdefault("name", {})
        item["collection"].setdefault("description", {})
    if item.get("weapon"):
        item["weapon"].setdefault("name", {})
        item["weapon"].setdefault("description", {})

    for language in languages:
        tokens = translations[language]
        item["name"][language] = tokens[item["name_key"]]
        item["description"][language] = tokens.get(item["description_key"], "")
        if item.get("collection"):
            item["collection"]["name"][language] = tokens[
                item["collection"]["name_key"]
            ]
            item["collection"]["description"][language] = tokens.get(
                item["collection"]["description_key"], ""
            )
        if item.get("weapon"):
            item["weapon"]["name"][language] = tokens[item["weapon"]["name_key"]]
            item["weapon"]["description"][language] = tokens.get(
                item["weapon"]["description_key"], ""
            )

    del item["name_key"]
    del item["description_key"]
    if item.get("collection"):
        del item["collection"]["name_key"]
        del item["collection"]["description_key"]
    if item.get("weapon"):
        del item["weapon"]["name_key"]
        del item["weapon"]["description_key"]


def run():
    items_game_path = game_path / "csgo" / "scripts" / "items" / "items_game.txt"
    items_game = load_vdf(items_game_path)

    items_game_cdn_path = (
        game_path / "csgo" / "scripts" / "items" / "items_game_cdn.txt"
    )
    items_game_cdn = load_items_game_cdn(items_game_cdn_path)

    translation_files_base_path = game_path / "csgo" / "resource"
    translations = {
        language: {
            k.lower().lstrip("#"): v
            for k, v in load_vdf(
                translation_files_base_path / f"csgo_{language}.txt",
                encoding="utf-16-le",
            )["lang"]["Tokens"].items()
        }
        for language in languages
    }

    print("[")

    collections = items_game["items_game"]["item_sets"].values()
    paint_kits = items_game["items_game"]["paint_kits"].values()
    prefabs = items_game["items_game"]["prefabs"]
    paint_kits_rarity = items_game["items_game"]["paint_kits_rarity"]
    items = items_game["items_game"]["items"].values()
    for i, item in enumerate(parse_collections(collections)):
        if i > 0:
            print(",")

        if item["type"] is ItemTypes.weapon_skin:
            fill_paintkit(item, paint_kits)
            fill_prefabs(item, prefabs)
            fill_rarity(item, paint_kits_rarity)
        fill_translations(item, translations)
        print(json.dumps(item))

    for item in parse_gloves(paint_kits_rarity):
        print(",")
        fill_paintkit(item, paint_kits)
        fill_glove_prefab(item, items)
        fill_rarity(item, paint_kits_rarity)
        fill_translations(item, translations)
        print(json.dumps(item))

    for item in parse_knives(items_game_cdn):
        print(",")
        fill_paintkit(item, paint_kits)
        fill_knife_prefab(item, items)
        fill_translations(item, translations)
        print(json.dumps(item))

    print("]")


if __name__ == "__main__":
    run()

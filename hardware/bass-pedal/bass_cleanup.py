#!/usr/bin/env python3
"""Replace guitar presets with a bass chain and drop the Factory Presets bank."""

from __future__ import annotations

import sys
import time

from pipedal_ws import PiPedalClient

BASS_CHAIN = [
    ("http://two-play.com/plugins/toob-tuner", "TooB Tuner"),
    ("http://two-play.com/plugins/toob-noise-gate", "TooB Noise Gate"),
    ("http://two-play.com/plugins/toob-parametric-eq", "TooB Parametric EQ"),
    ("http://two-play.com/plugins/toob-nam", "TooB Neural Amp Modeler"),
    ("http://two-play.com/plugins/toob-cab-ir", "TooB Cab IR"),
    ("http://two-play.com/plugins/toob-freeverb", "TooB Freeverb"),
]
EFFECT_CCS = [22, 23, 24, 25, 26, 27]
EMPTY_URIS = {
    "uri://two-play/pipedal/pedalboard#Empty",
}


def bypass_binding(cc: int) -> dict:
    return {
        "channel": -1,
        "symbol": "__bypass",
        "bindingType": 2,
        "note": 72,
        "control": cc,
        "minControlValue": 0,
        "maxControlValue": 127,
        "minValue": 0.0,
        "maxValue": 1.0,
        "rotaryScale": 1.0,
        "linearControlType": 0,
        "switchControlType": 0,
    }


def make_item(_template: dict, instance_id: int, uri: str, name: str, cc: int | None) -> dict:
    item = {
        "instanceId": instance_id,
        "uri": uri,
        "pluginName": name,
        "title": "",
        "isEnabled": True,
        "midiBindings": [bypass_binding(cc)] if cc is not None else [],
        "midiChannelBinding": None,
        "controlValues": [],
        "vstState": "",
        "stateUpdateCount": 0,
        "lv2State": [False, {}],
        "lilvPresetUri": "",
        "pathProperties": {},
        "useModUi": False,
        "iconColor": "",
        "sideChainInputId": -1,
    }
    return item


def wait_for_preset(ws: PiPedalClient, instance_id: int, timeout: float = 8.0) -> dict:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = ws.request("currentPedalboard")
        presets = ws.request("getPresets")
        if int(presets.get("selectedInstanceId", -1)) == instance_id:
            return last
        time.sleep(0.15)
    raise TimeoutError(f"preset {instance_id} did not load")


def main() -> int:
    ws = PiPedalClient()
    try:
        client_id = ws.hello()
        print("hello", client_id)
        plugins = {p.get("uri"): p for p in ws.request("plugins")}
        chain = []
        for uri, fallback in BASS_CHAIN:
            plugin = plugins.get(uri)
            if not plugin:
                print("missing plugin", uri)
                continue
            chain.append((uri, plugin.get("name") or fallback))
        if not chain:
            raise SystemExit("no bass-compatible plugins found")

        banks = ws.request("getBankIndex")
        factory_ids = [
            int(b["instanceId"])
            for b in (banks.get("entries") or [])
            if "factory" in (b.get("name") or "").lower()
        ]
        default_ids = [
            int(b["instanceId"])
            for b in (banks.get("entries") or [])
            if "default" in (b.get("name") or "").lower()
        ]
        if default_ids and int(banks.get("selectedBank", -1)) not in default_ids:
            ws.request("openBank", default_ids[0])
            time.sleep(0.3)

        presets = ws.request("getPresets")
        new_id = int(ws.request("newPreset"))
        print("new preset", new_id)
        ws.send("loadPreset", new_id)
        board = wait_for_preset(ws, new_id)
        template = {}
        for item in board.get("items") or []:
            if item.get("uri") not in EMPTY_URIS:
                template = item
                break
        if not template and board.get("items"):
            template = board["items"][0]

        next_id = int(board.get("nextInstanceId") or 100)
        items = []
        for i, (uri, name) in enumerate(chain):
            cc = EFFECT_CCS[i] if i < len(EFFECT_CCS) else None
            items.append(make_item(template, next_id, uri, name, cc))
            next_id += 1
        board["items"] = items
        board["nextInstanceId"] = next_id
        board["name"] = "Bass"
        ws.send("updateCurrentPedalboard", {"clientId": client_id, "pedalboard": board})
        time.sleep(0.2)
        ws.send("saveCurrentPreset", client_id)
        time.sleep(0.2)
        ws.request(
            "renamePresetItem",
            {"clientId": client_id, "instanceId": new_id, "name": "Bass"},
        )

        presets = ws.request("getPresets")
        to_delete = [
            int(p["instanceId"])
            for p in (presets.get("presets") or [])
            if int(p["instanceId"]) != new_id
        ]
        if to_delete:
            remaining = ws.request("deletePresetItems", to_delete)
            print("deleted presets, remaining selected", remaining)

        for fid in factory_ids:
            try:
                ws.request("deleteBankItem", fid)
                print("deleted factory bank", fid)
            except Exception as exc:
                print("could not delete factory bank", fid, exc)

        live = ws.request("currentPedalboard")
        print("live", live.get("name"), [i.get("pluginName") for i in live.get("items") or []])
        print("OK")
        return 0
    finally:
        ws.close()


if __name__ == "__main__":
    sys.exit(main())

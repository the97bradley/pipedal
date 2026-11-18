import { PluginType, UiPlugin } from './Lv2Plugin';

/** Guitar-only TooB plugins. NAM and Cab IR stay — they load bass files. */
const GUITAR_ONLY_URIS = new Set<string>([
    "http://two-play.com/plugins/toob-ml",
    "http://two-play.com/plugins/toob-power-stage-2",
    "http://two-play.com/plugins/toob-cab-sim",
]);

/** Real bass amps / tools. Fender Bassman is a guitar amp and is excluded below. */
const BASS_KEEP = /\b(svt|ampeg|aguilar|darkglass|markbass|gallien|hartke|bergantino|trace\s*elliot|octaver?|sub[- ]?octave)\b/i;

const GUITAR_NAMES = /\b(marshall|jcm|soldano|dumble|plexi|twin reverb|deluxe reverb|princeton|ac-?30|rectifier|mesa\s*boogie|metal zone|tube\s*screamer|ts-?9|ds-?1|pro\s*co\s*rat|big muff|bassman|guitarix|gx[_ ]?amp|blues\s*(jr|junior)|crunchbox|tumnus|wampler|rockman|mesaboogie|fender champ)\b/i;

const GUITAR_CAB_FILES = /\b(vintage uk|vintage us|80s uk|80s us|speaker 00)\b/i;

function haystack(plugin: Pick<UiPlugin, "uri" | "name" | "label" | "brand" | "plugin_display_type" | "description">): string {
    return [
        plugin.uri,
        plugin.name,
        plugin.label,
        plugin.brand,
        plugin.plugin_display_type,
        plugin.description,
    ].filter(Boolean).join(" ");
}

export function isBassCompatiblePlugin(plugin: Pick<UiPlugin, "uri" | "name"> & Partial<UiPlugin>): boolean {
    const uri = plugin.uri || "";
    const name = `${plugin.name || ""} ${plugin.label || ""}`;

    if (GUITAR_ONLY_URIS.has(uri)) {
        return false;
    }
    if (uri.includes("toob-ml") || uri.includes("toob-power-stage") || uri.includes("toob-cab-sim")) {
        return false;
    }
    if (uri.includes("toob-nam") || uri.includes("toob-cab-ir")) {
        return true;
    }
    if (BASS_KEEP.test(name) && !/bassman/i.test(name)) {
        return true;
    }

    const blob = haystack(plugin as UiPlugin);
    if (GUITAR_NAMES.test(blob)) {
        return false;
    }

    if (/guitarix|gxplugins/i.test(blob) || uri.includes("guitarix") || /\/gx[_-]/i.test(uri)) {
        return BASS_KEEP.test(name) && !/bassman/i.test(name);
    }

    if (plugin.plugin_type === PluginType.AmplifierPlugin) {
        return BASS_KEEP.test(name) && !/bassman/i.test(name);
    }
    if (plugin.plugin_type === PluginType.InstrumentPlugin) {
        return false;
    }
    return true;
}

export function isBassCompatibleFile(pathname: string, displayName: string, isDirectory: boolean): boolean {
    const label = `${displayName} ${pathname}`;
    const base = (displayName || "").replace(/\/+$/, "");
    if (pathname === "") {
        return true;
    }
    if (isDirectory) {
        if (/^Factory Models$/i.test(base) || /^Factory IRs$/i.test(base)) {
            return false;
        }
    }
    if (BASS_KEEP.test(label) && !/bassman/i.test(label)) {
        return true;
    }
    if (GUITAR_NAMES.test(label)) {
        return false;
    }
    if (/CabIR/i.test(pathname) && GUITAR_CAB_FILES.test(label)) {
        return false;
    }
    return true;
}

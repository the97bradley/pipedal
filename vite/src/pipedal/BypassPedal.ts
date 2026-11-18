import MidiBinding from './MidiBinding';
import { PedalboardItem } from './Pedalboard';

/** Footswitch pedals 1-6 send CC 22-27 (PCF P12-P17). */
export const BYPASS_PEDAL_COUNT = 6;
export const BYPASS_PEDAL_CC_BASE = 22;

export function isBypassableEffect(item: PedalboardItem): boolean {
    return !item.isEmpty() && !item.isSplit() && !item.isStart() && !item.isEnd();
}

export function getBypassPedal(item: PedalboardItem): number {
    const binding = item.getMidiBinding("__bypass");
    if (binding.bindingType !== MidiBinding.BINDING_TYPE_CONTROL) {
        return 0;
    }
    const pedal = binding.control - BYPASS_PEDAL_CC_BASE + 1;
    if (pedal < 1 || pedal > BYPASS_PEDAL_COUNT) {
        return 0;
    }
    return pedal;
}

export function makeBypassPedalBinding(pedal: number): MidiBinding {
    const binding = new MidiBinding();
    binding.symbol = "__bypass";
    if (pedal < 1 || pedal > BYPASS_PEDAL_COUNT) {
        binding.bindingType = MidiBinding.BINDING_TYPE_NONE;
        binding.control = 1;
        binding.switchControlType = MidiBinding.TOGGLE_ON_RISING_EDGE;
        return binding;
    }
    binding.bindingType = MidiBinding.BINDING_TYPE_CONTROL;
    binding.control = BYPASS_PEDAL_CC_BASE + pedal - 1;
    binding.minControlValue = 0;
    binding.maxControlValue = 127;
    binding.minValue = 0;
    binding.maxValue = 1;
    binding.switchControlType = MidiBinding.TOGGLE_ON_RISING_EDGE;
    return binding;
}

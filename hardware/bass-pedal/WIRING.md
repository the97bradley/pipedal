# Point-to-point wiring

All GPIO numbers below are **BCM**. Physical 40-pin header numbers are in parentheses. Do not interchange them.

## Raspberry Pi signals (10 distinct GPIOs)

| Function | BCM GPIO | Header pin | Goes to |
|---|---|---|---|
| HiFiBerry I2C SDA | 2 | 3 | HiFiBerry HAT only |
| HiFiBerry I2C SCL | 3 | 5 | HiFiBerry HAT only |
| SPI0 MOSI (OLED SDA/D1) | 10 | 19 | All six OLED `SDA` / `D1` / `MOSI` |
| SPI0 SCLK (OLED SCK/D0) | 11 | 23 | All six OLED `SCK` / `D0` / `CLK` |
| Expander I2C SDA | 22 | 15 | PCF8575 `SDA` |
| Expander I2C SCL | 23 | 16 | PCF8575 `SCL` |
| I2S BCLK | 18 | 12 | HiFiBerry HAT only |
| I2S LRCK | 19 | 35 | HiFiBerry HAT only |
| I2S ADC data | 20 | 38 | HiFiBerry HAT only |
| I2S DAC data | 21 | 40 | HiFiBerry HAT only |

Leave disconnected: header 24 / BCM 8 (SPI0 CE0), header 26 / BCM 7 (SPI0 CE1), header 27–28 (HAT ID EEPROM). Do not put the PCF8575 on BCM 2/3.

## Power and ground

| Net | Source | Load |
|---|---|---|
| `GND` | Pi header 6, 9, 14, 20, 25, 30, 34, 39 | HiFiBerry, PCF8575, every OLED, every footswitch, 3.3 V regulator |
| `5V` | Pi header 2 or 4 | HiFiBerry (via HAT), **OLED 3.3 V regulator VIN** |
| `3V3_EXP` | Pi header 1 or 17 | PCF8575 `VCC` only (a few milliamps) |
| `3V3_OLED` | Dedicated regulator from `5V`, ≥600 mA | All six OLED `VCC` pins and CS/DC/RES pull-ups |

HiFiBerry's GPIO guide: do not draw more than a few mA from the Pi 3.3 V rail. Six OLEDs can take ~120–240 mA all-white. Feed them from 5 V through their own 3.3 V LDO (AP2112K-3.3 or similar). Common ground is required.

If a specific OLED module already has an onboard 3.3 V regulator and is rated for 5 V on `VCC`, you may feed that module `5V` instead of `3V3_OLED`. Confirm the module, not the listing title. SPI `SCK`/`SDA`/`RES`/`DC`/`CS` on many 1.3" panels are **not** 5 V tolerant — keep those nets at 3.3 V.

## PCF8575

Default I2C address **0x20** with `A0`, `A1`, `A2` all low / jumpers open. Leave the INT pin unconnected (polling, no extra Pi GPIO).

| PCF8575 pin (breakout silk P0–P15) | Net | Notes |
|---|---|---|
| VCC | `3V3_EXP` | 2.5–5.5 V part, run at 3.3 V |
| GND | `GND` | |
| SDA | BCM 22 | 10 kΩ pull-up to 3.3 V if the breakout does not already have one |
| SCL | BCM 23 | same |
| P0 | `OLED1_CS` | Active low |
| P1 | `OLED2_CS` | Active low |
| P2 | `OLED3_CS` | Active low |
| P3 | `OLED4_CS` | Active low |
| P4 | `OLED5_CS` | Active low |
| P5 | `OLED6_CS` | Active low |
| P6 | `OLED_DC` | Shared; 0 = command, 1 = data |
| P7 | `OLED_RES` | Shared; pulse low to reset all six |
| P8 | `FS1` | Footswitch 1 to GND |
| P9 | `FS2` | |
| P10 | `FS3` | |
| P11 | `FS4` | |
| P12 | `FS5` | |
| P13 | `FS6` | |
| P14 | `FS7` | spare |
| P15 | `FS8` | spare |

Adafruit-style silk `P8–P15` is TI `P10–P17` (the second I2C data byte). Cheap boards sometimes label the high nibble `P10–P17`; match the silk to this table before soldering.

### Pull-ups

The PCF8575 high output is a weak current source (tens to hundreds of µA). Fit **4.7 kΩ–10 kΩ to 3.3 V** on `OLED1_CS`…`OLED6_CS`, `OLED_DC`, and `OLED_RES`. Fit the same on `FS1`…`FS8` (or use the expander's weak pull-up plus 10 kΩ). Footswitches are momentary SPST to ground.

Power-on: every expander pin is high, so every CS is inactive. Software still writes `0xFFFF` before any SPI transfer.

## OLED modules (each 7-pin SPI)

Typical silk, left to right: `GND`, `VCC`, `SCK`, `SDA`, `RES`, `DC`, `CS`. On these modules `SDA` is MOSI, not I2C.

| OLED pin | Net |
|---|---|
| GND | `GND` |
| VCC | `3V3_OLED` (or 5 V only if that exact module's regulator allows it) |
| SCK / D0 / CLK | BCM 11 / header 23 |
| SDA / D1 / MOSI | BCM 10 / header 19 |
| RES / RST | `OLED_RES` (PCF8575 P7) |
| DC / A0 | `OLED_DC` (PCF8575 P6) |
| CS / SS | `OLEDn_CS` (PCF8575 P0…P5) |

Controller: **SSD1306** on most 0.96" 128×64 panels, **SH1106** on most 1.3" 128×64 panels. Same wiring. Pass `--controller sh1106` if the image is shifted by two pixels or garbage with the SSD1306 init.

## HiFiBerry DAC+ ADC Pro

Sits on the 40-pin header. Overlay `dtoverlay=hifiberry-dacplusadcpro`.

Official GPIO map ([HiFiBerry GPIO usage](https://www.hifiberry.com/docs/hardware/gpio-usage-of-hifiberry-boards/), updated 2025-09-29): **BCM 2–3 and 18–21 only**. BCM 4 is not used on this product (it is used on Amp / DAC8x). Kernel overlay `hifiberry-dacplusadcpro-overlay.dts` binds `i2c1` (`pcm5122@4d`, `pcm186x@4a`) and stereo I2S — it does not claim BCM 10, 11, 22, or 23.

Keep the HAT on the Pi (short I2S). Bring OLED/expander wiring out with a **short stacking proto board or extra-tall header** under the HAT. Do not extend I2S on a long ribbon.

## Mechanical order (bottom to top)

1. Raspberry Pi
2. Short stacking header / proto HAT that exposes unused pins
3. HiFiBerry DAC+ ADC Pro
4. Wiring loom to the OLED/expander daughterboard in the pedal enclosure

## Footswitch wiring

Each switch: one side `FSn`, other side `GND`. Debounce is software (20 ms). Keep the loom away from the I2S and analog audio cables.

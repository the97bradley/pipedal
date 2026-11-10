# Bass pedal GPIO, OLEDs, and HiFiBerry

Headrush-style floorboard on a Raspberry Pi running PiPedal: **HiFiBerry DAC+ ADC Pro**, **six 7-pin SPI OLEDs**, **PCF8575** for chip-select / DC / reset and footswitches. The expander is on its own I2C bus. It never shares HiFiBerry's I2C1 (BCM 2/3).

The driver lives in `python/bass_pedal/` and must run in a process that is **not** the PiPedal audio thread.

## GPIO budget

Ten distinct BCM signals, matching the handoff:

| Subsystem | BCM | Header pins | Count |
|---|---|---|---:|
| HiFiBerry I2S | 18, 19, 20, 21 | 12, 35, 38, 40 | 4 |
| HiFiBerry I2C | 2, 3 | 3, 5 | 2 |
| OLED SPI0 MOSI, SCLK | 10, 11 | 19, 23 | 2 |
| PCF8575 I2C | 22, 23 | 15, 16 | 2 |
| **Total** | | | **10** |

Power, ground, and HAT ID pins (header 27/28) are extra and must stay reserved.

## Datasheet verification

Physical hardware was not on this agent host. The pin map is verified against published docs, not against a photographed board revision.

| Item | Result | Source |
|---|---|---|
| Pi model | **Pi 5 recommended** (PiPedal's target). Pi 4 (40-pin) is the fallback. | [PiPedal system requirements](../../docs/SystemRequirements.md); HiFiBerry [Pi 5 compatibility](https://www.hifiberry.com/blog/pi5-compatibility-with-hifiberry-products/) lists DAC+ ADC Pro as compatible |
| HiFiBerry product | DAC+ ADC Pro, overlay `hifiberry-dacplusadcpro` | [Datasheet](https://www.hifiberry.com/docs/data-sheets/datasheet-dac-adc-pro) |
| HiFiBerry GPIOs | BCM **2, 3, 18, 19, 20, 21** only. BCM 4 is **not** used on this board. | [GPIO usage of HiFiBerry boards](https://www.hifiberry.com/docs/hardware/gpio-usage-of-hifiberry-boards/) (2025-09-29) |
| Overlay claim | `i2c1` + stereo `i2s_clk_consumer`; codecs `pcm5122@4d`, `pcm186x@4a` | [hifiberry-dacplusadcpro-overlay.dts](https://github.com/raspberrypi/linux/blob/rpi-6.12.y/arch/arm/boot/dts/overlays/hifiberry-dacplusadcpro-overlay.dts) |
| BCM 10, 11, 22, 23 | Free for SPI0 and a second I2C. Not in the HiFiBerry map. Do not use the DAC8x overlay — that product **does** take 18–27 including 22/23 | Same GPIO usage page (DAC8x section) |
| Dedicated I2C | Pi 5: `dtoverlay=i2c3-pi5,pins_22_23`. Pi 4: `dtoverlay=i2c6,pins_22_23`. Bit-bang `i2c-gpio` is the fallback | [raspberrypi/linux overlays README](https://github.com/raspberrypi/linux/blob/rpi-6.12.y/arch/arm/boot/dts/overlays/README) |
| OLED | 7-pin SPI 128×64. `SDA` means MOSI. 0.96" ≈ SSD1306, 1.3" ≈ SH1106. Logic 3.3 V; `VCC` 3.3–5 V only if that module has a regulator | Module pinout + SH1106/SSD1306 datasheets |
| PCF8575 | Quasi-bidirectional, address 0x20–0x27 from A2/A1/A0, power-on all pins high, IOH ~30–300 µA | [TI PCF8575](https://www.ti.com/lit/ds/symlink/pcf8575.pdf); [Adafruit pinout](https://learn.adafruit.com/adafruit-pcf8575/pinouts) (default 0x20, 10 kΩ SDA/SCL pull-ups) |

Still to confirm on the bench: exact Pi SKU, HiFiBerry PCB revision printed on silk, OLED controller (SSD1306 vs SH1106) and whether `VCC` is 3.3 V-only, PCF8575 breakout pull-ups and address jumpers.

## Software chip-select

SPI0 is MOSI+SCLK only. `spidev.no_cs = True`. The PCF8575 drops **one** CS at a time, sets DC for the whole transfer, then raises CS. DC is never changed while a transfer is in flight. Shared RES is pulsed with every CS held high.

## Configure the Pi

1. Append [`config/config.txt.snippet`](config/config.txt.snippet) to `/boot/firmware/config.txt`.
2. Reboot.
3. `i2cdetect -l` — expect HiFiBerry on **bus 1** and the expander on bus 3 (Pi 5) or 6 (Pi 4).
4. `sudo i2cdetect -y 3` (or `6`) — expect `0x20` if A0/A1/A2 are low. **Do not scan bus 1.**
5. On the Pi:

```bash
cd hardware/bass-pedal/python
python3 -m pip install -r requirements.txt
python3 -m bass_pedal.bringup --scan
python3 -m bass_pedal.bringup --controller ssd1306
# 1.3" panels that look shifted or blank:
python3 -m bass_pedal.bringup --controller sh1106
```

Laptop check (no Pi):

```bash
cd hardware/bass-pedal/python
python3 -m bass_pedal.bringup --mock --once
python3 -m unittest discover -s tests -v
```

## Isolation from audio

PiPedal's ALSA/Jack thread must not talk to this expander. Run `bringup` (and any later UI daemon) as a normal-priority process. Footswitch events can later be turned into ALSA MIDI or PiPedal HTTP; that bridge is not in this tree yet.

## Files

| Path | What |
|---|---|
| [WIRING.md](WIRING.md) | Point-to-point nets |
| [config/config.txt.snippet](config/config.txt.snippet) | Overlays |
| [python/bass_pedal/](python/bass_pedal/) | PCF8575 + SSD1306/SH1106 + footswitch debounce |
| [python/tests/](python/tests/) | Mock-bus unit tests |

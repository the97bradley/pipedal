#!/bin/bash
# Run on the Pi as root: sudo bash ~/fix-bt-on-pi.sh
# SSP on, installs NAP/agent, kills bluetoothctl, restarts NAP.
set -euo pipefail
USER_HOME="${SUDO_USER:+$(getent passwd "$SUDO_USER" | cut -d: -f6)}"
USER_HOME="${USER_HOME:-/home/the97bradley}"

install -m 755 "$USER_HOME/pipedal-bt-nap" /usr/sbin/pipedal-bt-nap
install -m 755 "$USER_HOME/pipedal-bt-agent" /usr/sbin/pipedal-bt-agent
install -m 755 "$USER_HOME/pipedal-bt-auth" /usr/sbin/pipedal-bt-auth
install -m 644 "$USER_HOME/pipedal_bt_pin.py" /usr/sbin/pipedal_bt_pin.py
install -d /usr/lib/pipedal
install -m 644 "$USER_HOME/pipedal_bt_pin.py" /usr/lib/pipedal/pipedal_bt_pin.py

# bluetoothctl loops steal the PIN agent.
systemctl --user --machine="${SUDO_USER:-the97bradley}@.host" disable --now pipedal-bt-advertise.service 2>/dev/null || true
pkill -u "${SUDO_USER:-the97bradley}" -f "bluetoothctl" 2>/dev/null || true

hciconfig hci0 up || true
hciconfig hci0 sspmode 1
hciconfig hci0 class 0x020100
hciconfig hci0 piscan || true

systemctl restart bluetooth
sleep 1
systemctl restart pipedal-bt-nap
sleep 2
echo "SSP: $(hciconfig hci0 sspmode | tr '\n' ' ')"
echo "NAP: $(systemctl is-active pipedal-bt-nap)"
journalctl -u pipedal-bt-nap -n 8 --no-pager
echo "Pair pipedal, then http://172.21.0.1 or ssh 172.21.0.1"

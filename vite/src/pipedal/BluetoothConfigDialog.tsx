// Copyright (c) Robin E.R. Davies
//
// Permission is hereby granted, free of charge, to any person obtaining a copy of
// this software and associated documentation files (the "Software"), to deal in
// the Software without restriction, including without limitation the rights to
// use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
// the Software, and to permit persons to whom the Software is furnished to do so,
// subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
// FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
// COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
// IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
// CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import DialogEx from './DialogEx';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import Typography from '@mui/material/Typography';
import ResizeResponsiveComponent from './ResizeResponsiveComponent';
import BluetoothConfigSettings from './BluetoothConfigSettings';

export interface BluetoothConfigProps {
    open: boolean,
    bluetoothConfigSettings: BluetoothConfigSettings,
    onOk: (bluetoothConfigSettings: BluetoothConfigSettings) => void,
    onClose: () => void
}

export interface BluetoothConfigState {
    enabled: boolean;
    name: string;
    pin: string;
    allowNewDevices: boolean;
    nameError: boolean;
    nameErrorMessage: string;
    pinError: boolean;
    pinErrorMessage: string;
}

const BluetoothConfigDialog =
    class extends ResizeResponsiveComponent<BluetoothConfigProps, BluetoothConfigState> {

        constructor(props: BluetoothConfigProps) {
            super(props);
            this.state = {
                enabled: this.props.bluetoothConfigSettings.enable !== false,
                name: this.props.bluetoothConfigSettings.deviceName || "pipedal",
                pin: this.props.bluetoothConfigSettings.pin || "",
                allowNewDevices: this.props.bluetoothConfigSettings.allowNewDevices !== false,
                nameError: false,
                nameErrorMessage: "",
                pinError: false,
                pinErrorMessage: ""
            };
        }

        componentDidUpdate(prevProps: BluetoothConfigProps) {
            if (this.props.open && !prevProps.open) {
                this.setState({
                    enabled: this.props.bluetoothConfigSettings.enable !== false,
                    name: this.props.bluetoothConfigSettings.deviceName || "pipedal",
                    pin: this.props.bluetoothConfigSettings.pin || "",
                    allowNewDevices: this.props.bluetoothConfigSettings.allowNewDevices !== false,
                    nameError: false,
                    nameErrorMessage: "",
                    pinError: false,
                    pinErrorMessage: ""
                });
            }
        }

        handleOk() {
            let name = (this.state.name || "").trim();
            let pin = (this.state.pin || "").trim();
            if (this.state.enabled) {
                if (name.length === 0) {
                    this.setState({ nameError: true, nameErrorMessage: "* Required" });
                    return;
                }
                if (name.length > 32) {
                    this.setState({ nameError: true, nameErrorMessage: "Longer than 32 characters" });
                    return;
                }
                if (!/^[A-Za-z0-9 _-]+$/.test(name)) {
                    this.setState({ nameError: true, nameErrorMessage: "Use letters, numbers, space, - or _" });
                    return;
                }
                if (!/^[0-9]{4,8}$/.test(pin)) {
                    this.setState({ pinError: true, pinErrorMessage: "4 to 8 digits, required for every new device" });
                    return;
                }
            }
            let settings = new BluetoothConfigSettings();
            settings.valid = true;
            settings.enable = this.state.enabled;
            settings.deviceName = name.length ? name : "pipedal";
            settings.pin = pin;
            settings.allowNewDevices = this.state.allowNewDevices;
            this.props.onOk(settings);
        }

        render() {
            return (
                <DialogEx
                    tag="bluetoothConfig"
                    open={this.props.open}
                    onClose={() => this.props.onClose()}
                    fullWidth
                    maxWidth="sm"
                    onEnterKey={() => { this.handleOk(); }}
                >
                    <DialogTitle>Bluetooth remote</DialogTitle>
                    <DialogContent>
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={this.state.enabled}
                                    onChange={(e) => this.setState({ enabled: e.target.checked })}
                                />
                            }
                            label="Bluetooth remote (on by default)"
                        />
                        <TextField
                            autoComplete="off"
                            id="bt_device_name"
                            margin="dense"
                            label="Bluetooth name"
                            fullWidth
                            value={this.state.name}
                            error={this.state.nameError}
                            helperText={this.state.nameError ? this.state.nameErrorMessage : "Shown in iPad Settings → Bluetooth"}
                            onChange={(e) => this.setState({ name: e.target.value, nameError: false, nameErrorMessage: "" })}
                            disabled={!this.state.enabled}
                        />
                        <TextField
                            autoComplete="off"
                            id="bt_pin"
                            margin="dense"
                            label="Pairing PIN"
                            fullWidth
                            value={this.state.pin}
                            error={this.state.pinError}
                            helperText={this.state.pinError ? this.state.pinErrorMessage : "Required on every new device. 4–8 digits. Already-paired devices reconnect without it."}
                            inputProps={{ inputMode: "numeric", pattern: "[0-9]*", maxLength: 8 }}
                            onChange={(e) => this.setState({ pin: e.target.value, pinError: false, pinErrorMessage: "" })}
                            disabled={!this.state.enabled}
                        />
                        <FormControlLabel
                            control={
                                <Switch
                                    checked={this.state.allowNewDevices}
                                    onChange={(e) => this.setState({ allowNewDevices: e.target.checked })}
                                    disabled={!this.state.enabled}
                                />
                            }
                            label="Discoverable"
                        />
                        <Typography variant="body2" color="textSecondary" style={{ lineHeight: "1.45em" }}>
                            New devices must enter PIN {this.state.pin || "••••"}. Just Works pairing is rejected.
                            Forget any old “Connected” pairing that did not ask for a PIN — that was not the network.
                        </Typography>
                        <Typography variant="subtitle2" style={{ marginTop: 16 }}>How the iPad connects</Typography>
                        <Typography variant="body2" color="textSecondary" component="div" style={{ lineHeight: "1.45em" }}>
                            <ol style={{ paddingLeft: 20, marginTop: 8, marginBottom: 0 }}>
                                <li>iPad: Settings → Bluetooth → ⓘ on <b>{this.state.name || "pipedal"}</b> → Forget This Device.</li>
                                <li>Tap <b>{this.state.name || "pipedal"}</b> and enter PIN <b>{this.state.pin || "••••"}</b>.</li>
                                <li>Wait a few seconds. Open the main Settings list. <b>Ethernet</b> is the Bluetooth network — leave it Automatic (DHCP). Bluetooth “Connected” alone is not enough.</li>
                                <li>Safari: <b>http://172.21.0.1</b></li>
                            </ol>
                        </Typography>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={() => this.props.onClose()} color="secondary">
                            Cancel
                        </Button>
                        <Button onClick={() => this.handleOk()} color="secondary" disabled={!this.props.bluetoothConfigSettings.valid && !this.state.enabled}>
                            OK
                        </Button>
                    </DialogActions>
                </DialogEx>
            );
        }
    };

export default BluetoothConfigDialog;

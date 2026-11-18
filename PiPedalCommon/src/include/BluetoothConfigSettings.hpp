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
#pragma once

#include "json.hpp"
#include <string>

namespace pipedal {

    // Isolated Bluetooth PAN. No default route is advertised, so an iPad can
    // stay on Wi-Fi (or cellular) for internet while talking to PiPedal over BT.
    inline constexpr const char *BLUETOOTH_NAP_BRIDGE = "pan0";
    inline constexpr const char *BLUETOOTH_NAP_ADDRESS = "172.21.0.1";
    inline constexpr const char *BLUETOOTH_NAP_SERVICE = "pipedal-bt-nap";

    class BluetoothConfigSettings {
    public:
        BluetoothConfigSettings();

        void Load();
        void Save();

        bool HasBluetoothAdapter() const;
        void EnsurePin();

        // Bluetooth remote is the default iPad path and stays enabled
        // whenever an adapter is present.
        bool enable_ = true;
        std::string deviceName_ = "pipedal";
        // Required for every new pairing. Already-paired devices reconnect
        // without typing it again.
        std::string pin_;
        bool valid_ = false;

        DECLARE_JSON_MAP(BluetoothConfigSettings);
    };

} // namespace pipedal

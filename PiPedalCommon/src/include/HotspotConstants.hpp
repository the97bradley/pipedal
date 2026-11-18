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
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
// WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
// CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#pragma once

#include <chrono>
#include <cstdint>
#include <string_view>

namespace pipedal {

    // NetworkManager connection id for the auto-hotspot. Dispatcher scripts key off this name.
    inline constexpr const char *kPipedalHotspotConnectionId = "PiPedal Hotspot";

    // IPv4 address of the Pi when it is hosting the auto-hotspot.
    // Keep this in sync with NetworkManager dnsmasq-shared.d and the UI copy.
    inline constexpr const char *kPipedalHotspotIpv4 = "192.168.60.1";
    inline constexpr uint32_t kPipedalHotspotPrefixLength = 24;

    // Extra mDNS / DHCP DNS name that always resolves to the hotspot gateway.
    inline constexpr const char *kPipedalHotspotMdnsName = "pipedal";

    // How long to let NetworkManager try remembered Wi-Fi / Ethernet before
    // falling back to the auto-hotspot in NoNetworkConnection mode.
    inline constexpr std::chrono::seconds kHotspotConnectTimeout{45};

    inline bool IsPipedalHotspotIpv4(std::string_view ipv4)
    {
        return ipv4 == kPipedalHotspotIpv4 || ipv4 == "10.42.0.1";
    }

} // namespace pipedal

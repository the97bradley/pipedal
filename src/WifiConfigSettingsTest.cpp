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
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#include "pch.h"
#include "catch.hpp"
#include "WifiConfigSettings.hpp"
#include "HotspotConstants.hpp"

using namespace pipedal;

static WifiConfigSettings MakeSettings(HotspotAutoStartMode mode)
{
    WifiConfigSettings settings;
    settings.valid_ = true;
    settings.autoStartMode_ = (int16_t)mode;
    settings.homeNetwork_ = "HomeNet";
    settings.hasPassword_ = true;
    settings.password_ = "password";
    settings.hotspotName_ = "pipedal";
    return settings;
}

TEST_CASE("Hotspot auto-start wants hotspot", "[wifi_config][Build][Dev]")
{
    std::vector<std::string> none;
    std::vector<std::string> homeVisible{"HomeNet", "Cafe"};
    std::vector<std::string> rememberedVisible{"Cafe"};

    {
        auto settings = MakeSettings(HotspotAutoStartMode::Never);
        REQUIRE_FALSE(settings.WantsHotspot(false, false, none, none));
        REQUIRE_FALSE(settings.NeedsConnectionTimeout());
        REQUIRE_FALSE(settings.NeedsScan());
    }

    {
        auto settings = MakeSettings(HotspotAutoStartMode::Always);
        REQUIRE(settings.WantsHotspot(true, true, homeVisible, homeVisible));
        REQUIRE_FALSE(settings.NeedsConnectionTimeout());
    }

    {
        auto settings = MakeSettings(HotspotAutoStartMode::NoEthernetConnection);
        REQUIRE(settings.WantsHotspot(false, false, none, none));
        REQUIRE_FALSE(settings.WantsHotspot(true, false, none, none));
    }

    {
        auto settings = MakeSettings(HotspotAutoStartMode::NotAtHome);
        REQUIRE(settings.NeedsScan());
        REQUIRE(settings.WantsHotspot(false, false, none, none));
        REQUIRE_FALSE(settings.WantsHotspot(false, false, rememberedVisible, homeVisible));
    }

    {
        auto settings = MakeSettings(HotspotAutoStartMode::NoRememberedWifiConections);
        REQUIRE(settings.NeedsScan());
        REQUIRE(settings.WantsHotspot(false, false, none, none));
        REQUIRE_FALSE(settings.WantsHotspot(false, false, rememberedVisible, homeVisible));
    }

    {
        auto settings = MakeSettings(HotspotAutoStartMode::NoNetworkConnection);
        REQUIRE(settings.NeedsConnectionTimeout());
        REQUIRE_FALSE(settings.NeedsScan());
        REQUIRE(settings.WantsHotspot(false, false, none, none));
        REQUIRE(settings.WantsHotspot(false, false, rememberedVisible, homeVisible));
        REQUIRE_FALSE(settings.WantsHotspot(true, false, none, none));
        REQUIRE_FALSE(settings.WantsHotspot(false, true, none, none));
        REQUIRE_FALSE(settings.WantsHotspot(true, true, homeVisible, homeVisible));
    }

    {
        auto settings = MakeSettings(HotspotAutoStartMode::NoNetworkConnection);
        settings.valid_ = false;
        REQUIRE_FALSE(settings.WantsHotspot(false, false, none, none));
    }
}

TEST_CASE("Hotspot address constants", "[wifi_config][Build][Dev]")
{
    REQUIRE(IsPipedalHotspotIpv4(kPipedalHotspotIpv4));
    REQUIRE(IsPipedalHotspotIpv4("10.42.0.1"));
    REQUIRE_FALSE(IsPipedalHotspotIpv4("192.168.1.1"));
    REQUIRE(kHotspotConnectTimeout.count() == 45);
}

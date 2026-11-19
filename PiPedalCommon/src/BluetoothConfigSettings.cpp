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

#include "BluetoothConfigSettings.hpp"
#include "json.hpp"
#include "ofstream_synced.hpp"
#include "ss.hpp"
#include "Lv2Log.hpp"
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <cctype>
#include <cstdio>
#include <random>
#include <ctime>
#include <cstdint>

using namespace pipedal;
using namespace std;
namespace fs = std::filesystem;

static const fs::path CONFIG_PATH = "/var/pipedal/config/bluetoothConfig.json";

JSON_MAP_BEGIN(BluetoothConfigSettings)
    JSON_MAP_REFERENCE(BluetoothConfigSettings, valid)
    JSON_MAP_REFERENCE(BluetoothConfigSettings, enable)
    JSON_MAP_REFERENCE(BluetoothConfigSettings, deviceName)
    JSON_MAP_REFERENCE(BluetoothConfigSettings, pin)
    JSON_MAP_REFERENCE(BluetoothConfigSettings, allowNewDevices)
    JSON_MAP_REFERENCE(BluetoothConfigSettings, pairingUntil)
JSON_MAP_END()

namespace {

bool IsValidBluetoothPin(const std::string &pin)
{
    if (pin.size() < 4 || pin.size() > 8)
    {
        return false;
    }
    for (char c : pin)
    {
        if (!std::isdigit(static_cast<unsigned char>(c)))
        {
            return false;
        }
    }
    return true;
}

std::string GenerateBluetoothPin()
{
    std::random_device rd;
    std::uniform_int_distribution<int> dist(0, 999999);
    char buf[16];
    std::snprintf(buf, sizeof(buf), "%06d", dist(rd));
    return buf;
}

} // namespace

void BluetoothConfigSettings::EnsurePin()
{
    if (!IsValidBluetoothPin(pin_))
    {
        pin_ = GenerateBluetoothPin();
    }
}

BluetoothConfigSettings::BluetoothConfigSettings()
{
    Load();
}

bool BluetoothConfigSettings::HasBluetoothAdapter() const
{
    try
    {
        fs::path bluetoothClass("/sys/class/bluetooth");
        if (!fs::exists(bluetoothClass) || !fs::is_directory(bluetoothClass))
        {
            return false;
        }
        for (const auto &entry : fs::directory_iterator(bluetoothClass))
        {
            (void)entry;
            return true;
        }
    }
    catch (const std::exception &)
    {
    }
    return false;
}

void BluetoothConfigSettings::Load()
{
    try
    {
        if (fs::exists(CONFIG_PATH))
        {
            std::ifstream f(CONFIG_PATH);
            if (!f)
            {
                throw std::runtime_error("Can't open file.");
            }
            json_reader reader(f);
            reader.read(this);
        }
        if (deviceName_.empty())
        {
            deviceName_ = "pipedal";
        }
        valid_ = HasBluetoothAdapter();
    }
    catch (const std::exception &e)
    {
        throw std::runtime_error(SS("Can't load BluetoothConfigSettings. " << e.what()));
    }
}

void BluetoothConfigSettings::Save()
{
    BluetoothConfigSettings toSave{*this};
    if (toSave.deviceName_.empty())
    {
        toSave.deviceName_ = "pipedal";
    }
    for (char c : toSave.deviceName_)
    {
        if (!(std::isalnum(static_cast<unsigned char>(c)) || c == '-' || c == '_' || c == ' '))
        {
            throw std::runtime_error("Bluetooth device name contains invalid characters.");
        }
    }
    if (toSave.deviceName_.size() > 32)
    {
        throw std::runtime_error("Bluetooth device name is longer than 32 characters.");
    }
    toSave.EnsurePin();
    if (!IsValidBluetoothPin(toSave.pin_))
    {
        throw std::runtime_error("Bluetooth PIN must be 4 to 8 digits.");
    }
    if (!toSave.allowNewDevices_)
    {
        toSave.pairingUntil_ = 0;
    }

    auto directory = CONFIG_PATH.parent_path();
    if (!fs::exists(directory))
    {
        fs::create_directories(directory);
    }

    pipedal::ofstream_synced f(CONFIG_PATH.string());
    if (!f)
    {
        throw std::runtime_error(SS("Can't write " << CONFIG_PATH.string()));
    }
    json_writer writer(f, false);
    writer.write(&toSave);
}

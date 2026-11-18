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

#include "SetBluetoothConfig.hpp"
#include "WriteTemplateFile.hpp"
#include "SysExec.hpp"
#include "ss.hpp"
#include "Lv2Log.hpp"
#include <filesystem>
#include <map>

using namespace pipedal;
using namespace std;
namespace fs = std::filesystem;

#define SYSTEMCTL_BIN "/usr/bin/systemctl"
#define SERVICE_PATH "/usr/lib/systemd/system"

static fs::path ServiceFile()
{
    return fs::path(SERVICE_PATH) / SS(BLUETOOTH_NAP_SERVICE << ".service");
}

static void EnsureServiceUnitInstalled()
{
    std::map<std::string, std::string> map;
    map["DESCRIPTION"] = "PiPedal Bluetooth network (iPad/phone remote)";
    map["COMMAND"] = "/usr/sbin/pipedal-bt-nap";
    try
    {
        WriteTemplateFile(map, ServiceFile());
    }
    catch (const std::exception &e)
    {
        // Template is installed with the package. Ignore if we are running from a tree
        // that has not been installed yet.
        Lv2Log::warning(SS("Bluetooth NAP service unit not installed: " << e.what()));
        return;
    }
    silentSysExec(SYSTEMCTL_BIN " daemon-reload");
}

void pipedal::SetBluetoothConfig(const BluetoothConfigSettings &settings)
{
    BluetoothConfigSettings copy = settings;
    if (copy.deviceName_.empty())
    {
        copy.deviceName_ = "pipedal";
    }
    copy.EnsurePin();
    copy.Save();

    EnsureServiceUnitInstalled();
    if (!fs::exists(ServiceFile()))
    {
        if (copy.enable_)
        {
            throw std::runtime_error("Bluetooth NAP service is not installed. Re-run pipedalconfig --install after building this version.");
        }
        return;
    }

    if (copy.enable_)
    {
        if (!copy.HasBluetoothAdapter())
        {
            throw std::runtime_error("No Bluetooth adapter was found.");
        }
        if (silentSysExec(SS(SYSTEMCTL_BIN " enable " << BLUETOOTH_NAP_SERVICE << ".service").c_str()) != EXIT_SUCCESS)
        {
            throw std::runtime_error("Failed to enable the Bluetooth NAP service.");
        }
        if (silentSysExec(SS(SYSTEMCTL_BIN " restart " << BLUETOOTH_NAP_SERVICE << ".service").c_str()) != EXIT_SUCCESS)
        {
            throw std::runtime_error("Failed to start the Bluetooth NAP service. Is BlueZ installed?");
        }
    }
    else
    {
        silentSysExec(SS(SYSTEMCTL_BIN " stop " << BLUETOOTH_NAP_SERVICE << ".service").c_str());
        silentSysExec(SS(SYSTEMCTL_BIN " disable " << BLUETOOTH_NAP_SERVICE << ".service").c_str());
    }
}

void pipedal::OnBluetoothInstall()
{
    EnsureServiceUnitInstalled();
    BluetoothConfigSettings settings;
    settings.Load();
    if (!settings.HasBluetoothAdapter())
    {
        Lv2Log::info("No Bluetooth adapter found; Bluetooth remote not started.");
        return;
    }
    settings.enable_ = true;
    if (settings.deviceName_.empty())
    {
        settings.deviceName_ = "pipedal";
    }
    settings.EnsurePin();
    SetBluetoothConfig(settings);
}

void pipedal::OnBluetoothUninstall()
{
    silentSysExec(SS(SYSTEMCTL_BIN " stop " << BLUETOOTH_NAP_SERVICE << ".service").c_str());
    silentSysExec(SS(SYSTEMCTL_BIN " disable " << BLUETOOTH_NAP_SERVICE << ".service").c_str());
    try
    {
        fs::remove(ServiceFile());
    }
    catch (...)
    {
    }
}

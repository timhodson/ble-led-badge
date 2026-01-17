#!/usr/bin/env python3
import asyncio
from bleak import BleakScanner

async def scan_devices():
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    if devices:
        print("Found devices:")
        for i, device in enumerate(devices, start=1):
            print(f"{i}. {device.name} - {device.address}")
    else:
        print("No devices found.")

if __name__ == "__main__":
    asyncio.run(scan_devices())
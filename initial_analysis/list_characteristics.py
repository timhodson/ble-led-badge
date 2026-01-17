#!/usr/bin/env python3
import asyncio
from bleak import BleakClient

async def list_characteristics(address):
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        services = await client.get_services()
        print("Listing characteristics:")
        for service in services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}")
                print(f"    Properties: {char.properties}")
                try:
                    value = await client.read_gatt_char(char.uuid)
                    print(f"Value of {char.uuid}: {value}")
                except Exception as e:
                    print(f"  Error reading {char.uuid}: {e}")
                for descriptor in char.descriptors:
                    print(f"    Descriptor: {descriptor.uuid}")

async def read_characteristic(address, uuid):
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        value = await client.read_gatt_char(uuid)
        print(f"Value of {uuid}: {value}")

if __name__ == "__main__":

    ADDRESS = "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"  # Replace with your device's address
    UUID = "d44bc439-abfd-45a2-b575-925416129601"  # Replace with the characteristic UUID
    asyncio.run(list_characteristics(ADDRESS))
    # asyncio.run(read_characteristic(ADDRESS, UUID))
#!/usr/bin/env python3
import sys
import asyncio
from bleak import BleakClient

ADDRESS = "FE5DCE05-1120-2974-BCBF-7AE2F6A509DF"
FEE1_CHARACTERISTIC = "d44bc439-abfd-45a2-b575-925416129600"

WRITE_REQUESTS = [
    "77616E67000000000000000000000000",
    "00050000000000000000000000000000",
    "000000000000E10C06172D2300000000",
    "00000000000000000000000000000000",
    "00C6C6C6C6FEC6C6C6C600000000007C",
    "C6FEC0C67C000038181818181818183C",
    "000038181818181818183C0000000000",
    "7CC6C6C6C67C00000000000000000000"
]

async def main(address):
    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")
        for i in range (0, len(WRITE_REQUESTS)):
            byte_array = bytes.fromhex(WRITE_REQUESTS[i])
            await client.write_gatt_char(FEE1_CHARACTERISTIC, byte_array, response=True)
            print(f"Written bytearray: {str(byte_array)}")

asyncio.run(main(ADDRESS))
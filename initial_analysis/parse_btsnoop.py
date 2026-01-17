#!/usr/bin/env python3
"""
BTSnoop log parser to extract BLE GATT writes for LED badge protocol analysis.
"""
import struct
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class BTSnoopHeader:
    identification: bytes  # 8 bytes: 'btsnoop\0'
    version: int          # 4 bytes: version number
    datalink_type: int    # 4 bytes: datalink type (1001 = HCI UART)


@dataclass
class BTSnoopRecord:
    original_length: int
    included_length: int
    packet_flags: int
    cumulative_drops: int
    timestamp: int  # microseconds since midnight Jan 1, 2000
    data: bytes


@dataclass
class ATTWriteRequest:
    handle: int
    value: bytes


def parse_btsnoop_header(data: bytes) -> BTSnoopHeader:
    """Parse BTSnoop file header."""
    if len(data) < 16:
        raise ValueError("Invalid BTSnoop header: too short")

    ident = data[0:8]
    if ident != b'btsnoop\x00':
        raise ValueError(f"Invalid BTSnoop identification: {ident}")

    version = struct.unpack('>I', data[8:12])[0]
    datalink = struct.unpack('>I', data[12:16])[0]

    return BTSnoopHeader(ident, version, datalink)


def parse_btsnoop_record(data: bytes, offset: int) -> tuple[BTSnoopRecord, int]:
    """Parse a single BTSnoop record starting at offset."""
    if offset + 24 > len(data):
        raise ValueError("Insufficient data for record header")

    orig_len, incl_len, flags, drops = struct.unpack('>IIII', data[offset:offset+16])
    timestamp = struct.unpack('>Q', data[offset+16:offset+24])[0]

    record_data = data[offset+24:offset+24+incl_len]
    new_offset = offset + 24 + incl_len

    return BTSnoopRecord(orig_len, incl_len, flags, drops, timestamp, record_data), new_offset


def parse_hci_packet(data: bytes) -> dict:
    """Parse HCI packet and extract relevant info."""
    if len(data) < 1:
        return {'type': 'unknown', 'data': data}

    # HCI packet types
    HCI_COMMAND = 0x01
    HCI_ACL = 0x02
    HCI_SCO = 0x03
    HCI_EVENT = 0x04

    # For BTSnoop with Unencapsulated HCI, packets start with HCI type
    packet_type = data[0]

    if packet_type == HCI_ACL and len(data) > 5:
        # ACL packet: type(1) + handle(2) + length(2) + data
        handle_flags = struct.unpack('<H', data[1:3])[0]
        conn_handle = handle_flags & 0x0FFF
        acl_len = struct.unpack('<H', data[3:5])[0]
        acl_data = data[5:5+acl_len]

        return {
            'type': 'ACL',
            'conn_handle': conn_handle,
            'data': acl_data,
            'raw': data
        }

    return {'type': hex(packet_type) if packet_type else 'unknown', 'data': data}


def parse_l2cap(acl_data: bytes) -> Optional[dict]:
    """Parse L2CAP layer from ACL data."""
    if len(acl_data) < 4:
        return None

    l2cap_len = struct.unpack('<H', acl_data[0:2])[0]
    cid = struct.unpack('<H', acl_data[2:4])[0]
    l2cap_data = acl_data[4:4+l2cap_len]

    # CID 0x0004 is ATT (Attribute Protocol)
    return {
        'length': l2cap_len,
        'cid': cid,
        'cid_name': 'ATT' if cid == 0x0004 else f'CID:{cid:04x}',
        'data': l2cap_data
    }


def parse_att(l2cap_data: bytes) -> Optional[dict]:
    """Parse ATT (Attribute Protocol) PDU."""
    if len(l2cap_data) < 1:
        return None

    ATT_OPCODES = {
        0x01: 'Error Response',
        0x02: 'Exchange MTU Request',
        0x03: 'Exchange MTU Response',
        0x04: 'Find Information Request',
        0x05: 'Find Information Response',
        0x06: 'Find By Type Value Request',
        0x07: 'Find By Type Value Response',
        0x08: 'Read By Type Request',
        0x09: 'Read By Type Response',
        0x0A: 'Read Request',
        0x0B: 'Read Response',
        0x0C: 'Read Blob Request',
        0x0D: 'Read Blob Response',
        0x10: 'Read By Group Type Request',
        0x11: 'Read By Group Type Response',
        0x12: 'Write Request',
        0x13: 'Write Response',
        0x16: 'Prepare Write Request',
        0x17: 'Prepare Write Response',
        0x18: 'Execute Write Request',
        0x19: 'Execute Write Response',
        0x1B: 'Handle Value Notification',
        0x1D: 'Handle Value Indication',
        0x1E: 'Handle Value Confirmation',
        0x52: 'Write Command (no response)',
    }

    opcode = l2cap_data[0]
    result = {
        'opcode': opcode,
        'opcode_name': ATT_OPCODES.get(opcode, f'Unknown(0x{opcode:02x})'),
        'data': l2cap_data[1:]
    }

    # Parse Write Request (0x12) and Write Command (0x52)
    if opcode in (0x12, 0x52) and len(l2cap_data) >= 3:
        handle = struct.unpack('<H', l2cap_data[1:3])[0]
        value = l2cap_data[3:]
        result['handle'] = handle
        result['value'] = value

    return result


def analyze_trace(filepath: Path, verbose: bool = False, show_all_att: bool = False):
    """Analyze a single BTSnoop trace file."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {filepath.name}")
    print('='*60)

    data = filepath.read_bytes()

    try:
        header = parse_btsnoop_header(data)
        print(f"BTSnoop Version: {header.version}, Datalink: {header.datalink_type}")
    except ValueError as e:
        print(f"Error parsing header: {e}")
        return

    offset = 16  # After header
    record_num = 0
    writes = []
    all_att_ops = []

    while offset < len(data):
        try:
            record, offset = parse_btsnoop_record(data, offset)
            record_num += 1

            # Debug: print first few records raw data
            if verbose and record_num <= 10:
                print(f"\nRecord {record_num}: flags={record.packet_flags} len={record.included_length}")
                print(f"  Raw: {record.data.hex()}")

            # BTSnoop with Unencapsulated HCI (datalink 1001) has packets
            # in HCI H4 format but without the H4 type byte
            # The packet_flags field indicates direction and type:
            # - Bit 0: 0=host->controller, 1=controller->host
            # - Bit 1: 0=data, 1=command/event

            # For ACL data packets (flags bit 1 = 0), parse directly as ACL
            is_received = record.packet_flags & 0x01
            is_command_event = record.packet_flags & 0x02

            if not is_command_event and len(record.data) >= 4:
                # This is an ACL data packet
                # ACL header: handle(2) + length(2) + data
                handle_flags = struct.unpack('<H', record.data[0:2])[0]
                conn_handle = handle_flags & 0x0FFF
                acl_len = struct.unpack('<H', record.data[2:4])[0]
                acl_data = record.data[4:4+acl_len]

                if verbose and record_num <= 10:
                    print(f"  ACL: handle={conn_handle}, len={acl_len}")
                    print(f"  ACL data: {acl_data.hex()}")

                l2cap = parse_l2cap(acl_data)
                if l2cap:
                    if verbose and record_num <= 10:
                        print(f"  L2CAP: cid={l2cap['cid']:04x} ({l2cap['cid_name']})")

                    if l2cap['cid'] == 0x0004:  # ATT
                        att = parse_att(l2cap['data'])
                        if att:
                            if verbose or att['opcode'] in (0x12, 0x52):
                                print(f"  ATT: {att['opcode_name']}")

                            # Record ALL ATT operations for analysis
                            all_att_ops.append({
                                'record': record_num,
                                'opcode': att['opcode'],
                                'opcode_name': att['opcode_name'],
                                'handle': att.get('handle'),
                                'value': att.get('value'),
                                'data': att.get('data'),
                                'direction': 'recv' if is_received else 'send'
                            })

                            if att['opcode'] in (0x12, 0x52):  # Write Request/Command
                                writes.append({
                                    'record': record_num,
                                    'handle': att['handle'],
                                    'value': att['value'],
                                    'opcode': att['opcode_name'],
                                    'direction': 'recv' if is_received else 'send'
                                })

        except (ValueError, struct.error) as e:
            if verbose:
                print(f"Error at record {record_num}: {e}")
            break

    print(f"\nTotal records: {record_num}")
    print(f"Total ATT operations: {len(all_att_ops)}")
    print(f"Write operations found: {len(writes)}")

    if show_all_att:
        print("\n--- All ATT Operations ---")
        for op in all_att_ops:
            print(f"\nRecord #{op['record']}: {op['opcode_name']} ({op['direction']})")
            if op.get('handle'):
                print(f"  Handle: 0x{op['handle']:04x}")
            if op.get('value'):
                print(f"  Value: {op['value'].hex()}")
            elif op.get('data'):
                print(f"  Data: {op['data'].hex()}")

    if writes:
        print("\n--- Write Operations ---")
        for w in writes:
            hex_val = w['value'].hex()
            print(f"\nRecord #{w['record']}: {w['opcode']}")
            print(f"  Handle: 0x{w['handle']:04x}")
            print(f"  Value ({len(w['value'])} bytes): {hex_val}")
            # Also print in grouped format
            grouped = ' '.join(hex_val[i:i+4] for i in range(0, len(hex_val), 4))
            print(f"  Grouped: {grouped}")

    return writes


def compare_writes(all_writes: dict):
    """Compare write operations across different traces."""
    print("\n" + "="*60)
    print("COMPARISON OF WRITE VALUES ACROSS TRACES")
    print("="*60)

    for name, writes in all_writes.items():
        if writes:
            print(f"\n{name}:")
            for i, w in enumerate(writes):
                print(f"  Write {i+1}: Handle 0x{w['handle']:04x} = {w['value'].hex()}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Parse BTSnoop logs')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-a', '--all-att', action='store_true', help='Show all ATT operations')
    parser.add_argument('file', nargs='?', help='Specific file to analyze')
    args = parser.parse_args()

    traces_dir = Path(__file__).parent / 'traces'

    if args.file:
        trace_files = [Path(args.file)]
    else:
        trace_files = sorted(traces_dir.glob('*.log'))

    if not trace_files:
        print("No .log trace files found in traces/")
        return

    all_writes = {}

    for trace_file in trace_files:
        writes = analyze_trace(trace_file, verbose=args.verbose, show_all_att=args.all_att)
        all_writes[trace_file.stem] = writes

    compare_writes(all_writes)


if __name__ == '__main__':
    main()

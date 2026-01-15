"""
AES-ECB encryption for BLE LED Badge commands.

The badge uses AES in ECB mode with a fixed key for command encryption.
"""

from Crypto.Cipher import AES

from .protocol import AES_KEY, BLOCK_SIZE


def pad_to_block_size(data: bytes) -> bytes:
    """Pad data to AES block size (16 bytes) with zeros."""
    if len(data) >= BLOCK_SIZE:
        return data[:BLOCK_SIZE]
    return data + bytes(BLOCK_SIZE - len(data))


def encrypt_command(data: bytes) -> bytes:
    """
    Encrypt a command packet using AES-ECB.

    Args:
        data: Raw command bytes (will be padded to 16 bytes)

    Returns:
        16-byte encrypted packet
    """
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    padded = pad_to_block_size(data)
    return cipher.encrypt(padded)


def decrypt_response(data: bytes) -> bytes:
    """
    Decrypt a response packet using AES-ECB.

    Args:
        data: 16-byte encrypted response

    Returns:
        Decrypted bytes (with padding)
    """
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    return cipher.decrypt(data)


def build_encrypted_packet(command: str, *args: int) -> bytes:
    """
    Build and encrypt a command packet.

    Packet format: [length][command ASCII][args...][padding]

    Args:
        command: ASCII command string (e.g., "LIGHT", "ANIM")
        *args: Optional byte arguments

    Returns:
        16-byte encrypted packet ready to send
    """
    cmd_bytes = command.encode('ascii')
    arg_bytes = bytes(args)
    payload = cmd_bytes + arg_bytes

    # Length prefix is total length of command + args
    length_byte = bytes([len(payload)])
    packet = length_byte + payload

    return encrypt_command(packet)

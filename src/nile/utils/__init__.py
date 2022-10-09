"""Utilities for Nile scripting."""

import math
from pathlib import Path

from nile.common import ABIS_DIRECTORY, BUILD_DIRECTORY

try:
    from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash
    from starkware.starknet.business_logic.execution.objects import Event
    from starkware.starknet.core.os.class_hash import compute_class_hash
    from starkware.starknet.public.abi import get_selector_from_name
    from starkware.starknet.services.api.contract_class import ContractClass
    from starkware.starkware_utils.error_handling import StarkException
except BaseException:
    pass

MAX_UINT256 = (2**128 - 1, 2**128 - 1)
INVALID_UINT256 = (MAX_UINT256[0] + 1, MAX_UINT256[1])
ZERO_ADDRESS = 0
TRUE = 1
FALSE = 0

TRANSACTION_VERSION = 0


_root = Path(__file__).parent.parent


def contract_path(name):
    """Return contract path."""
    if name.startswith("tests/"):
        return str(_root / name)
    else:
        return str(_root / "src" / name)


def str_to_felt(text):
    """Return a field element from a given string."""
    b_text = bytes(text, "ascii")
    return int.from_bytes(b_text, "big")


def felt_to_str(felt):
    """Return a string from a given field element."""
    felt = int(felt, 16) if "0x" in felt else int(felt)
    b_felt = felt.to_bytes(31, "big")
    return b_felt.decode()


def to_uint(a):
    """Return uint256-ish tuple from value."""
    a = int(a)
    return (a & ((1 << 128) - 1), a >> 128)


def from_uint(uint):
    """Return value from uint256-ish tuple."""
    return uint[0] + (uint[1] << 128)


def add_uint(a, b):
    """Return the sum of two uint256-ish tuples."""
    a = from_uint(a)
    b = from_uint(b)
    c = a + b
    return to_uint(c)


def sub_uint(a, b):
    """Return the difference of two uint256-ish tuples."""
    a = from_uint(a)
    b = from_uint(b)
    c = a - b
    return to_uint(c)


def mul_uint(a, b):
    """Return the product of two uint256-ish tuples."""
    a = from_uint(a)
    b = from_uint(b)
    c = a * b
    return to_uint(c)


def div_rem_uint(a, b):
    """Return the quotient and remainder of two uint256-ish tuples."""
    a = from_uint(a)
    b = from_uint(b)
    c = math.trunc(a / b)
    m = a % b
    return (to_uint(c), to_uint(m))


async def assert_revert(fun, reverted_with=None):
    """Raise if passed function does not revert."""
    try:
        await fun
        raise AssertionError("Transaction did not revert")
    except StarkException as err:
        _, error = err.args
        if reverted_with is not None:
            assert reverted_with in error["message"]


async def assert_revert_entry_point(fun, invalid_selector):
    """Raise is passed function does not revert with invalid selector."""
    selector_hex = hex(get_selector_from_name(invalid_selector))
    entry_point_msg = f"Entry point {selector_hex} not found in contract"

    await assert_revert(fun, entry_point_msg)


def assert_event_emitted(tx_exec_info, from_address, name, data):
    """Raise if event and event items do not match."""
    assert (
        Event(
            from_address=from_address,
            keys=[get_selector_from_name(name)],
            data=data,
        )
        in tx_exec_info.raw_events
    )


def get_contract_class(contract_name, overriding_path=None):
    """Return the contract_class for a given contract name."""
    base_path = (
        overriding_path if overriding_path else (BUILD_DIRECTORY, ABIS_DIRECTORY)
    )
    with open(f"{base_path[0]}/{contract_name}.json", "r") as fp:
        contract_class = ContractClass.loads(fp.read())

    return contract_class


def get_hash(contract_name, overriding_path=None):
    """Return the class_hash for a given contract name."""
    contract_class = get_contract_class(contract_name, overriding_path)
    return compute_class_hash(contract_class=contract_class, hash_func=pedersen_hash)


def normalize_number(number):
    """Normalize hex or int to int."""
    if type(number) == str and number.startswith("0x"):
        return int(number, 16)
    else:
        return int(number)


def hex_address(number):
    """Return the 64 hexadecimal characters length address."""
    if type(number) == str and number.startswith("0x"):
        return _pad_hex_to_64(number)
    else:
        return _pad_hex_to_64(hex(int(number)))


def _pad_hex_to_64(hexadecimal):
    if len(hexadecimal) < 66:
        missing_zeros = 66 - len(hexadecimal)
        return hexadecimal[:2] + missing_zeros * "0" + hexadecimal[2:]

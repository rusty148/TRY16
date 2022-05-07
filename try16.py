from typing import Any, Union
from boa3.builtin import CreateNewEvent, NeoMetadata, metadata, public
from boa3.builtin.type import UInt160
from boa3.builtin.contract import Nep17TransferEvent, abort
from boa3.builtin.interop import storage, runtime
from boa3.builtin.interop.runtime import calling_script_hash, check_witness
from boa3.builtin.interop.contract import call_contract
from boa3.builtin.interop.blockchain import get_contract
from boa3.builtin.nativecontract.neo import NEO as NEO_TOKEN
from boa3.builtin.nativecontract.contractmanagement import ContractManagement
from boa3.builtin.interop.runtime import check_witness


# -------------------------------------------
# CONSTANTS
# -------------------------------------------

OWNER = UInt160("NZ52Yd3sNcV1aCJTh9NRmSY1c8J7JbWds8".to_script_hash())
TOKEN_SYMBOL = 'TRY16'
SUPPLY_KEY = 'totalSupply'
TOKEN_DECIMALS = 8
TOKEN_TOTAL_SUPPLY = 100*10**TOKEN_DECIMALS

# -------------------------------------------
# Events
# -------------------------------------------

on_transfer = Nep17TransferEvent

# -------------------------------------------
# NEP-17 Methods
# -------------------------------------------

@public
def symbol() -> str:
    return TOKEN_SYMBOL

@public
def decimals() -> int:
    return TOKEN_DECIMALS

@public
def totalSupply() -> int:
    return storage.get(SUPPLY_KEY).to_int()

@public(name='totalSupply', safe=True)
def total_supply() -> int:
    """
    Gets the total token supply deployed in the system.

    This number must not be in its user representation. E.g. if the total supply is 10,000,000 tokens, this method
    must return 10,000,000 * 10 ^ decimals.

    :return: the total token supply deployed in the system.
    """
    return storage.get(SUPPLY_KEY).to_int()


@public(name='balanceOf', safe=True)
def balance_of(account: UInt160) -> int:
    """
    Get the current balance of an address.

    The parameter account must be a 20-byte address represented by a UInt160.

    :param account: the account address to retrieve the balance for
    :type account: bytes
    """
    assert len(account) == 20
    return storage.get(account).to_int()



@public
def balanceOf(account: UInt160) -> int:
    assert len(account) == 20, 'invalid address'
    
    return storage.get(account).to_int()

@public
def transfer(from_address: UInt160, to_address: UInt160, amount: int, data: Any) -> bool:
    assert len(from_address) == 20 and len(to_address) == 20, 'invalid address'
    assert amount >= 0, 'invalid amount'
    
    from_balance = storage.get(from_address).to_int()
    if from_balance < amount:
        return False
        
    if from_address != calling_script_hash:
        if not check_witness(from_address):
            return False

    if from_address != to_address and amount != 0:
        if from_balance == amount:
            storage.delete(from_address)
        else:
            storage.put(from_address, from_balance - amount)

        to_balance = storage.get(to_address).to_int()
        storage.put(to_address, to_balance + amount)

    on_transfer(from_address, to_address, amount)

    contract = get_contract(to_address)
    if not isinstance(contract, None):
        call_contract(to_address, 'onNEP17Payment', [from_address, amount, data])

    return True


def post_transfer(from_address: Union[UInt160, None], to_address: Union[UInt160, None], amount: int, data: Any,
                  call_onPayment: bool):
    """
    Checks if the one receiving NEP17 tokens is a smart contract and if it's one the onPayment method will be called.

    :param from_address: the address of the sender
    :type from_address: UInt160
    :param to_address: the address of the receiver
    :type to_address: UInt160
    :param amount: the amount of cryptocurrency that is being sent
    :type amount: int
    :param data: any pertinent data that might validate the transaction
    :type data: Any
    :param call_onPayment: whether onPayment should be called or not
    :type call_onPayment: bool
    """
    if call_onPayment:
        if not isinstance(to_address, None):  # TODO: change to 'is not None' when `is` semantic is implemented
            contract = ContractManagement.get_contract(to_address)
            if not isinstance(contract, None):  # TODO: change to 'is not None' when `is` semantic is implemented
                call_contract(to_address, 'onNEP17Payment', [from_address, amount, data])

# -------------------------------------------
# Other Methods
# -------------------------------------------


@public(safe=True)
def update(nef_file: bytes, manifest: bytes):
    """
    Updates the smart contract.
    """
    if check_witness(OWNER):
        ContractManagement.update(nef_file, manifest)

@public
def _deploy(data: Any, update: bool):
    if update:
        return
    
    if storage.get(SUPPLY_KEY).to_int() > 0:
        return

    storage.put(SUPPLY_KEY, TOKEN_TOTAL_SUPPLY)
    storage.put(OWNER, TOKEN_TOTAL_SUPPLY)

    on_transfer(None, OWNER, TOKEN_TOTAL_SUPPLY)

@public
def onNEP17Payment(from_address: UInt160, amount: int, data: Any):
    abort()


@public(safe=True)
def burn(account: UInt160, amount: int):
    """

    :param account: the address of the account that is pulling out cryptocurrency of this contract
    :type account: UInt160
    :param amount: the amount of gas to be refunded
    :type amount: int
    :raise AssertionError: raised if `account` length is not 20, amount is less than than 0 or the account doesn't have
    enough tokens to burn
    """
    assert len(account) == 20
    assert amount >= 0
    if runtime.check_witness(account):
        if amount != 0:
            current_total_supply = total_supply()
            account_balance = balance_of(account)

            assert account_balance >= amount

            storage.put(SUPPLY_KEY, current_total_supply - amount)

            if account_balance == amount:
                storage.delete(account)
            else:
                storage.put(account, account_balance - amount)

            on_transfer(account, None, amount)
            post_transfer(account, None, amount, None, False)

            NEO_TOKEN.transfer(runtime.executing_script_hash, account, amount)


# -------------------------------------------
# Manifest method with Contract's metadata
# -------------------------------------------

@metadata
def manifest_metadata() -> NeoMetadata:
    meta = NeoMetadata()
    meta.author = "updaterusty"
    meta.description = "updateNEP-17"
    meta.email = "updaterobigoyal7@gmail.com"
    meta.version = "0.01"
    meta.extras = {'Date of creation': '7 Feb 2022',
                   }
    return meta

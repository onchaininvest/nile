"""Command to call or invoke StarkNet smart contracts."""
import logging
import os

from dotenv import load_dotenv

from nile import accounts, deployments
from nile.common import UNIVERSAL_DEPLOYER_ADDRESS, is_alias
from nile.core.call_or_invoke import call_or_invoke
from nile.core.declare import declare
from nile.core.deploy import deploy
from nile.utils import get_contract_class, normalize_number
from nile.utils.get_nonce import get_nonce_without_log as get_nonce

try:
    from nile.signer import Signer
except ImportError:
    pass

load_dotenv()


class Account:
    """Account contract abstraction."""

    def __init__(self, signer, network, predeployed_info=None):
        """Get or deploy an Account contract for the given private key."""
        try:
            if predeployed_info is None:
                self.signer = Signer(normalize_number(os.environ[signer]))
                self.alias = signer
            else:
                self.signer = Signer(signer)
                self.alias = predeployed_info["alias"]

            self.network = network
        except KeyError:
            logging.error(
                f"\n❌ Cannot find {signer} in env."
                "\nCheck spelling and that it exists."
                "\nTry moving the .env to the root of your project."
            )
            return

        self.abi_path = os.path.dirname(os.path.realpath(__file__)).replace(
            "/core", "/artifacts/abis/Account.json"
        )

        if predeployed_info is not None:
            self.address = predeployed_info["address"]
            self.index = predeployed_info["index"]
        elif accounts.exists(self.signer.public_key, network):
            signer_data = next(accounts.load(self.signer.public_key, network))
            self.address = signer_data["address"]
            self.index = signer_data["index"]
        else:
            address, index = self.deploy()
            self.address = address
            self.index = index

    def deploy(self):
        """Deploy an Account contract for the given private key."""
        index = accounts.current_index(self.network)
        pt = os.path.dirname(os.path.realpath(__file__)).replace("/core", "")
        overriding_path = (f"{pt}/artifacts", f"{pt}/artifacts/abis")

        address, _ = deploy(
            "Account",
            [self.signer.public_key],
            self.network,
            f"account-{index}",
            overriding_path,
        )

        accounts.register(
            self.signer.public_key, address, index, self.alias, self.network
        )

        return address, index

    def declare(
        self, contract_name, max_fee=None, nonce=None, alias=None, overriding_path=None
    ):
        """Declare a contract through an Account contract."""
        if nonce is None:
            nonce = get_nonce(self.address, self.network)

        if max_fee is None:
            max_fee = 0
        else:
            max_fee = int(max_fee)

        contract_class = get_contract_class(
            contract_name=contract_name, overriding_path=overriding_path
        )

        sig_r, sig_s = self.signer.sign_declare(
            sender=self.address,
            contract_class=contract_class,
            nonce=nonce,
            max_fee=max_fee,
        )

        return declare(
            sender=self.address,
            contract_name=contract_name,
            signature=[sig_r, sig_s],
            alias=alias,
            network=self.network,
            max_fee=max_fee,
        )

    def deploy_contract(
        self, class_hash, salt, unique, calldata, max_fee=None, deployer_address=None
    ):
        """Deploy a contract through an Account contract."""
        return self.send(
            to=deployer_address or UNIVERSAL_DEPLOYER_ADDRESS,
            method="deployContract",
            calldata=[class_hash, salt, unique, len(calldata), *calldata],
            max_fee=max_fee,
        )

    def send(self, to, method, calldata, max_fee=None, nonce=None):
        """Execute a tx going through an Account contract."""
        if not is_alias(to):
            to = normalize_number(to)

        try:
            target_address, _ = next(deployments.load(to, self.network))
        except StopIteration:
            target_address = to

        calldata = [int(x) for x in calldata]

        if nonce is None:
            nonce = get_nonce(self.address, self.network)

        if max_fee is None:
            max_fee = 0
        else:
            max_fee = int(max_fee)

        calldata, sig_r, sig_s = self.signer.sign_transaction(
            sender=self.address,
            calls=[[target_address, method, calldata]],
            nonce=nonce,
            max_fee=max_fee,
        )

        return call_or_invoke(
            contract=self,
            type="invoke",
            method="__execute__",
            params=calldata,
            network=self.network,
            signature=[str(sig_r), str(sig_s)],
            max_fee=str(max_fee),
        )

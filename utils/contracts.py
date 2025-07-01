from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Contract:
    address: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for k, v in self.extra.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {"address": self.address, **self.extra}

    def __repr__(self):
        return f"<Contract address={self.address} extra={[k for k in self.extra]}>"


@dataclass
class Network:
    chain_id: int = None
    contracts: Dict[str, Contract] = field(default_factory=dict)

    def add_contract(self, name: str, address: str, **kwargs):
        self.contracts[name] = Contract(address, kwargs)

    def __getattr__(self, name: str) -> Contract:
        if name in self.contracts:
            return self.contracts[name]
        raise AttributeError(f"No contract named '{name}'")

    def __getitem__(self, name: str) -> Contract:
        return self.contracts[name]


class Contracts:
    def __init__(self):
        self.networks: Dict[str, Network] = {}

    def add_network(self, name: str, chain_id: int = None):
        self.networks[name] = Network(chain_id=chain_id)

    def add_contract(
        self, network_name: str, contract_name: str, address: str, **kwargs
    ):
        if network_name not in self.networks:
            self.add_network(network_name)
        self.networks[network_name].add_contract(contract_name, address, **kwargs)

    def load_from_dict(self, data: Dict[str, dict]):
        for network_name, contracts_data in data.items():
            chain_id = contracts_data.pop("chain_id", None)
            self.add_network(network_name, chain_id=chain_id)

            for contract_name, values in contracts_data.items():
                if not isinstance(values, dict) or "address" not in values:
                    raise ValueError(
                        f"Invalid contract definition for {network_name}.{contract_name}"
                    )

                address = values["address"]
                extra = {k: v for k, v in values.items() if k != "address"}
                self.add_contract(network_name, contract_name, address, **extra)

    def __getattr__(self, name: str) -> Network:
        if name in self.networks:
            return self.networks[name]
        raise AttributeError(f"No network named '{name}'")

    def __getitem__(self, name: str) -> Network:
        return self.networks[name]

    def __repr__(self):
        return f"<Contracts networks={list(self.networks.keys())}>"


contract_dict = {
    "base": {
        "chain_id": 8453,
        "mint": {"address": "0x7D5aCbAEE4aCcAA4c6fF9ca3F663DD9C28F5df6E"},
        "reward": {"address": "0x1f735280C83f13c6D40aA2eF213eb507CB4c1eC7"},
        "sponsor": {"address": "0x252683e292d7E36977de92a6BF779d6Bc35176D4"},
    },
    "ton": {
        "mint": {"address": "UQCn9hCC6tNykDqZisfJvwrE9RQNPalV8VArNWrmI_REtoHz"},
        "reward": {
            "address": "EQCfcwvBP2cnD8UwWLKtX1pcAqEDFwFyXzuZ0seyPBdocPHu",
            "usdt_reward_wallet": "EQAZh80U8AFlJBWxS5f90LhCF7q4Y6x4vVddxCDjfG-LgBRF",
        },
    },
}

CONTRACTS = Contracts()
CONTRACTS.load_from_dict(contract_dict)

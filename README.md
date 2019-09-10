# Bunkr Wallet

Bunkr Wallet is a simple bitcoin wallet application built on top of Bunkr. In utilizing Bunkr our wallet shifts the paradigm of cryptocurrency wallet security: private keys are distributedly stored in Bunkr and transaction signatures are securely generated without ever recomposing the private key on *any* device. The wallet is a bare bones proof of concept which can be controlled easily through a python interactive terminal. 

Disclaimer: test with caution, this wallet is in beta and under rapid development. Demo the wallet with testnet coins, and never publish generated transactions without decoding and looking them over first!

Notes: 
- Private keys are encrypted and stored across a distributed set of machines as Bunkr secrets and never touch your local machine.
- In order to create a wallet or send funds from a wallet, the Bunkr RPC must be running in the background.
- Bunkr Wallet is not an HD (heirarchical deterministic) wallet as wallet addresses are in no way correlated or derived from a master seed. One can add more addresses to the wallet keyring at anytime. Already used addresses with an unspent balance of 0 are automatically removed by the wallet, so always get a new receiving address for every invoice.
- A wallet stores all public wallet information in a simple json file. It stores addresses, public keys, and reference to Bunkr secrets (for communicating with the private key distributed across remote servers). While your private keys will still be safe and secure, losing the wallet file can make it a pain to recover funds from your wallet.

## Installation

Install the Bunkr Wallet (and all underlying requirements) with:

`pip3 install bunkrwallet`

## Usage

To start using bunkrwallet python library run:

```$ python3
>>> from bunkrwallet import BunkrWallet
>>> bw = BunkrWallet()```

## BunkrWallet class methods

```>>> bw = BunkrWallet()```

Creates an instance of the BunkrWallet.

Optional parameters (don't change these unless you know what you are doing):

- `directory` is the BunkrWallet directory (where all wallet files are stored)
- `bunkr_address` is the tuple (ip, port) containing Bunkr RPC address information (how python communicates with Bunkr backend)

#### create_wallet

```>>> w = bw.create_wallet("your-wallet-name")```

Creates Wallet object and the file `your-wallet-name.json` in the BunkrWallet directory.

Optional parameter

- `testnet` is a boolean flag for either bitcoin testnet or mainnet (defaults to False, i.e. mainnet)

#### list_wallets

```>>> bw.list_wallets()
['your-wallet-name', 'your-other-wallet-name', ...]```

Lists all the wallet names in the BunkrWallet directory.

#### get_wallet

```>>> w = bw.get_wallet("your-wallet-name")
```

Gets Wallet object with the name "your-wallet-name" from the BunkrWallet.

## Wallet class methods

#### show_balance

```>>> w.show_balance()```

Prints the total balance of the wallet.

#### show_fresh_address

```>>> w.show_fresh_address()```

Shows an unused address on the wallet keyring. Use this method to get an address for receiving bitcoin. If there are no fresh addresses left in the wallet it will raise an error (to overcome this error see add_addresses)

#### send

```>>> w.send([{"address": <address 1>, "value": <satoshi amount to address 1}, {"address": <address 2>, "value": <satoshi amount to address 2>}, ...], <fee amount>)```

Returns the signed transaction hex of a new bitcoin transaction. It is left to the user to publish the transaction.

#### add_addresses

```>>> w.add_addresses(<number of addresses>)```

Adds an amount of addresses to the wallet keyring.

## Testnet Demo

from this directory open a python3 interactive terminal:
```
$ python3
>>> from bunkrwallet import BunkrWallet
>>> bw = BunkrWallet()
>>> wallet = bw.create_wallet("testnetWallet", testnet=True)
'creating new wallet...'
>>> wallet.show_fresh_address()
<shows an unused address in your wallet, for receiving>
```

1. Create a new wallet with a wallet name of your choice. Set the testnet flag to True.
2. Get a fresh address for receiving bitcoin with show_fresh_address()
3. Send testnet bitcoins to your address. Testnet bitcoins can be found at a testnet faucet such as: https://coinfaucet.eu/en/btc-testnet/
4. Once you have some test bitcoin you can send from your wallet as in this example transaction:

```
>>> from bunkrwallet import BunkrWallet, COIN
>>> bw = BunkrWallet()
>>> wallet = bw.get_wallet("testnetWallet")
>>> wallet.show_balance()
<shows total wallet balance>
>>> outputs = [{"address":<some address>, "value":0.01*COIN}, ...]
>>> fee = 0.0001*COIN
>>> wallet.send(outputs, fee)
<prints transaction hex which can be pushed to the blockchain>
```

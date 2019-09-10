import os, json, time
from bunkrwallet.btc import *
from math import ceil
from random import shuffle

from punkr import *


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WALLET_DIR = os.path.join(CURRENT_DIR, ".BunkrWallet")
if not os.path.exists(DEFAULT_WALLET_DIR):
	os.mkdir(DEFAULT_WALLET_DIR)

class BunkrWallet(object):
	"""
	BunkrWallet is the class which creates and manages all Wallets in the provided wallet directory.
	A Wallet in BunkrWallet is a lite bitcoin wallet working on top of Bunkr secrets
	"""
	def __init__(self, directory=DEFAULT_WALLET_DIR, bunkr_address=("127.0.0.1", 7860)):
		"""
		:param directory: path to the directory where wallet json files are stored
		:param bunkr_address: (ip, port) tuple containing Bunkr RPC address information
		"""
		self.wallets = {}
		self.directory = directory
		self.bunkr_address = bunkr_address
		for file in os.listdir(directory):
			if file.endswith(".json"):
				try:
					name = file[:-5]
					w = Wallet(name, os.path.join(directory, file), bunkr_address, True)
					self.wallets[name] = w
				except:
					pass

	def create_wallet(self, name, testnet=False):
		"""
		Create a new bitcoin wallet in BunkrWallet
		:param name: wallet name
		:param testnet: boolean flag for mainnet vs testnet wallet
		:return: Wallet object
		"""		
		if name in list(self.wallets.keys()):
			raise ValueError(f"A wallet with the name '{name}' already exists")
		w = Wallet(name, os.path.join(self.directory, name+".json"), self.bunkr_address, testnet)
		self.wallets[name] = w
		return w

	def list_wallets(self):
		"""
		list wallet names in BunkrWallet
		:return: list of wallet names
		"""
		return list(self.wallets.keys())

	def get_wallet(self, name):
		"""
		get a wallet indexed by its name
		:param name: name to be queried
		:return: Wallet object
		"""
		return self.wallets[name]

	def delete_wallet(self, wallet):
		"""
		completely delete wallet and all associated accounts, indexed by its name
		:param name: name to be queried
		"""
		for acct in wallet.wallet:
			wallet.delete(acct)
		wallet.delete(wallet.name)
		os.remove(wallet.filepath)
		self.wallets.pop(wallet.name)


class Wallet(object):
	"""
	Wallet is a lite bitcoin wallet working on top of Bunkr secrets
	"""
	def __init__(self, wallet_name, wallet_filepath, bunkr_address, testnet):
		"""
		:param wallet_name: wallet name
		:param wallet_filepath: path to wallet json file
		:param bunkr_address: (ip, port) tuple containing Bunkr RPC address information
		:param testnet: boolean flag for mainnet vs testnet wallet
		"""
		self.punkr = Punkr(*bunkr_address)
		if not os.path.exists(wallet_filepath):
			print("Creating new bunkrwallet...")
			new_wallet(self.punkr, wallet_name, wallet_filepath, testnet)
		with open(wallet_filepath, 'r') as f:
			wallet_file = json.load(f)
		self.name = wallet_name
		self.filepath = wallet_filepath
		self.header = wallet_file[0]
		self.wallet = wallet_file[1:]
		self.testnet = self.header["NETWORK"] != "BTC"
		if time.time()>int(self.header["LAST_UPDATE_TIME"])+604800:
			self.__update_accounts()

	def send(self, outputs, fee):
		"""
		Send bitcoin to bitcoin addresses
		:param outputs: bitcoin addresses [{"address":address, "value":number_of_satoshis}]
		:param fee: transactions fee in satoshis
		:return: signed transaction hex code
		:raise: RuntimeError
		"""
		total = sum(i['value'] for i in outputs) + fee
		input_accts = self.__choose_inputs(total)
		change_acct = self.__fresh_account()
		tx, address_list = unsigned_transaction([i["address"] for i in input_accts], outputs, fee, change_acct["address"], self.testnet)
		acct_list = [self.__get_account(address) for address in address_list]
		pubkey_list = [acct["pubkey_hex"] for acct in acct_list]
		sec_name_list = [acct["secret_name"] for acct in acct_list]
		hash_list = [str(base64.b64encode(i), 'utf-8') for i in prepare_signatures(tx, pubkey_list)]
		commands = [
			("sign-ecdsa", {"secret_name": secret_name, "hash_content": _hash}) for secret_name, _hash in zip(sec_name_list, hash_list)
		]
		stdout = list(x.strip().split() for x in self.punkr.batch_commands(*commands))
		sigs = []
		try:
			for r, s in stdout:
				r = int(base64.b64decode(r))
				s = int(base64.b64decode(s))
				if s > N//2:
					s = N - s
				sigs.append((r, s))
		except:
			raise RuntimeError(f"Bunkr Operation SIGN-ECDSA failed with: {stdout}")
		return apply_signatures(tx, pubkey_list, sigs)

	def add_addresses(self, n=5):
		"""
		adds more addresses to the wallet
		:param n: number of addresses to be added
		:return: None
		"""
		for i in range(n):
			priv, pub = gen_EC_keypair()
			address = convert_public_to_address(pub, self.testnet)
			write_private_key_to_bunkr(self.punkr, priv, address, self.name)
			self.wallet.append({"address": address, "pubkey_hex":pub, "secret_name":name})
		output = [self.header, *self.wallet]
		with open(self.filepath, 'w') as f:
			json.dump(output, f)

	def show_balance(self):
		"""
		prints the wallet balance
		:return: None
		"""
		balance = 0
		for acct in self.wallet:
			utxos = get_unspent(acct["address"], self.testnet)
			balance += sum(i['value'] for i in utxos)
		print(f"{self.name} current balance: {str(balance/100000000.0)} BTC")

	def show_addresses(self):
		"""
		prints information about each individual address in the wallet
		:return: None
		"""
		for acct in self.wallet:
			utxos = get_unspent(acct["address"], self.testnet)
			balance = sum(i['value'] for i in utxos)
			print(f"Address {acct['address']} BTC: {str(balance/100000000.0)}")

	def show_fresh_address(self):
		"""
		prints the next unused bitcoin address
		:return: None
		"""
		print(self.__fresh_account()["address"])

	def delete(self, account):
		"""
		deletes an address from Bunkr
		:param account: account to be deleted
		:return: None
		"""
		stdout = self.punkr.delete(account["secret_name"])
		if stdout != 'Secret deleted\n':
			print(f"Bunkr Operation DELETE failed with: {stdout}")

	def __get_account(self, address):
		"""
		get the account information from a bitcoin address
		:param address: address to be queried
		:return: account
		:raise: ValueError
		"""
		for acct in self.wallet:
			if acct["address"] == address:
				return acct
		raise ValueError("The given address does not exist in the bunkrwallet")

	def __fresh_account(self):
		"""
		Randomly selects an unused bunkrwallet account
		:return: account
		:raise: ValueError
		"""
		shuffle(self.wallet)
		for acct in self.wallet:
			if len(get_spent(acct["address"], self.testnet))==0 and len(get_unspent(acct["address"], self.testnet))==0:
				return acct
		raise ValueError("No unused addresses available. Run add_accounts()")

	def __choose_inputs(self, total):
		"""
		choose which unspent transaction outputs are 
		:param total: number of total satoshis needed for transaction and fees
		:return: list of accounts all 
		:raise:
		"""
		out = []
		gross_input = 0
		shuffle(self.wallet)
		for acct in self.wallet:
			utxos = get_unspent(acct["address"], self.testnet)
			if len(utxos) != 0:
				out.append(acct)
				gross_input += sum(i['value'] for i in utxos)
			if gross_input >= total:
				return out
		raise ValueError(f"Not enough funds in wallet for this transaction: need: {total}, have: {gross_input}.")

	def __update_accounts(self):
		"""
		delete any fully spent and used addresses to keep wallet up to date
		:return: None
		"""
		deletes = []
		for acct in self.wallet:
			if len(get_unspent(acct["address"], self.testnet))==0:
				spent = get_spent(acct["address"], self.testnet)
				confirm = (s["confirmations"] >= 6 for s in spent)
				if len(spent) > 0 and all(confirm):
					deletes.append(acct)
		self.wallet = [acct for acct in self.wallet if acct not in deletes]
		self.header["LAST_UPDATE_TIME"] = str(round(time.time()))
		output = [self.header,] + self.wallet
		with open(self.filepath, 'w') as f:
			json.dump(output, f)
		for acct in deletes:
			self.delete(acct)

def new_wallet(punkr, wallet_name, wallet_filepath, testnet):
	"""
	generates a new wallet file
	:param punkr: punkr instance
	:param wallet_name: name of wallet
	:param wallet_filepath: filepath for wallet json file storage
	:param testnet: boolean flag for mainnet vs testnet wallet
	:return: None
	"""
	network = "BTCTEST" if testnet else "BTC"
	n_accounts = 5
	wallet_file = [{"NETWORK": network, "LAST_UPDATE_TIME": str(round(time.time()))}]
	write_wallet_group(punkr, wallet_name)
	for i in range(n_accounts):
		priv, pub = gen_EC_keypair()
		address = convert_public_to_address(pub, testnet)
		write_private_key_to_bunkr(punkr, priv, address, wallet_name)
		wallet_file.append({"address": address, "pubkey_hex":pub, "secret_name":address})
	with open(wallet_filepath, 'w') as f:
		json.dump(wallet_file, f)

def write_private_key_to_bunkr(punkr, private_key, address, wallet_name):
	"""
	writes a bitcoin private key to bunkr
	:param punkr: punkr instance
	:param private_key: bitcoin private key
	:param name: bunkr secret name
	:return: None
	"""
	for _ in punkr.batch_commands(
		("create", {"secret_name":address, "secret_type":"ECDSA-SECP256k1", "group_name": wallet_name}),
		("write",  {"secret_name":address, "content": "b64 "+ str(base64.b64encode(private_key.to_bytes(ceil(private_key.bit_length() / 8), 'big')), 'utf-8')})
	):
		pass

def write_wallet_group(punkr, wallet_name):
	resp = punkr.new_group(wallet_name)
	if resp != "Secret created\n":
		print(f"Bunkr Operation NEW-GROUP failed with: {resp}")



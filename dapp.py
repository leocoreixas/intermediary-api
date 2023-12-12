from os import environ
import logging
import requests
import datetime
import json
import random
import traceback
from eth_abi.abi import encode
from eth_abi_ext import decode_packed

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server =  "http://localhost:8080/host-runner" or environ["ROLLUP_HTTP_SERVER_URL"]
network = "localhost"

logger.info(f"HTTP rollup_server url is {rollup_server}")
logger.info(f"Network is {network}")

# Function selector to be called during the execution of a voucher that transfers funds,
# which corresponds to the first 4 bytes of the Keccak256-encoded result of "withdrawEther(address,uint256)"
WITHDRAW_FUNCTION_SELECTOR = b'R/h\x15'

# Setup contracts addresses
dapp_address_relay_file = open(f'./deployments/{network}/DAppAddressRelay.json')
dapp_address_relay = json.load(dapp_address_relay_file)

ETHERPortalFile = open(f'./deployments/{network}/EtherPortal.json')
etherPortal = json.load(ETHERPortalFile) 

CLIENTS = []
OFFERS = []
BALANCES = {}
VOUCHERS = {}
STATUS_CODES = [
    "accepted",
    "refused",
    "pending",
    "reoffered"
]


class Offer:
    def __init__(self, id, name, description, user_id, original_offer_id, proposer_id,
                 offer_value, image, status, ended, created_at, ended_at, updated_at,
                 country, state, city, street, zipcode, number, complement, selectedType, productType):
        self.id = id
        self.name = name
        self.description = description
        self.user_id = user_id
        self.original_offer_id = original_offer_id
        self.proposer_id = proposer_id
        self.offer_value = offer_value
        self.image = image
        self.status = status
        self.ended = ended
        self.created_at = created_at
        self.updated_at = updated_at
        self.ended_at = ended_at
        self.country = country
        self.state = state
        self.city = city
        self.street = street
        self.zipcode = zipcode
        self.number = number
        self.complement = complement
        self.selectedType = selectedType
        self.productType = productType

    def get_values(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'proposer_id': self.proposer_id,
            'original_offer_id': self.original_offer_id,
            'offer_value': self.offer_value,
            'image': self.image,
            'status': self.status,
            'ended': self.ended,
            'created_at': self.created_at,
            'ended_at': self.ended_at,
            'updated_at': self.updated_at,
            'country': self.country,
            'state': self.state,
            'city': self.city,
            'street': self.street,
            'zipcode': self.zipcode,
            'number': self.number,
            'complement': self.complement,
            'selectedType': self.selectedType,
            'productType': self.productType,
        }

    def createOffer(data):
        OFFERS.append(data)
        return True

    def updateOffer(id):
        for offer in OFFERS:
            # todo remove all offers with same original_offer_id
            if offer.id == id or offer.original_offer_id == id:
                OFFERS.remove(offer)
        return True

    def getOffer(id):
        offer = OFFERS[id]
        return offer

    def getOffersPending():
        offers_values = []
        for offer in OFFERS:
            if offer.status == 'pending':
                values = offer.get_values()
                offers_values.append(values)
        return offers_values

    def getAllOffers():
        offers_values = []
        for offer in OFFERS:
            values = offer.get_values()
            offers_values.append(values)
        return offers_values

    def getReOffers():
        offers_values = []
        for offer in OFFERS:
            if offer.status == 'reoffered':
                values = offer.get_values()
                offers_values.append(values)
        return offers_values

    def accept_proposal(payload):
        try:
            offer = Offer.getOffer(payload['id'])
            if not offer:
                return False
            if payload['user_id'] not in BALANCES:
                BALANCES[payload['user_id']] = 0
            BALANCES[payload['user_id']] += payload['offer_value']
            if payload['proposer_id'] not in BALANCES:
                BALANCES[payload['proposer_id']] = 0
            BALANCES[payload['proposer_id']] -= payload['offer_value']
            Offer.updateOffer(payload['id'])
            Offer.updateOffer(payload['original_offer_id'])

            return True
        except Exception as e:
            return False
        
    def generate_withdrawal(payload):
        try:
            user_id = payload['user_id']
            if user_id not in BALANCES:
                return False
            payload_balance = float(payload['balance'])
            BALANCES[user_id] = float(BALANCES[user_id])
            if payload_balance > BALANCES[user_id]:
                return False
            
            address = payload['address']
            amount = int(payload_balance)
            user_address = payload['user_address']

            withdraw_payload = WITHDRAW_FUNCTION_SELECTOR + encode(['address','uint256'], [user_address, amount])
            voucher = {"destination": address, "payload": "0x" + withdraw_payload.hex()}
            response = requests.post(rollup_server + "/voucher", json=voucher)
            print("Voucher response status ", response.status_code)
            print("Voucher response body ", response.content)
            
            BALANCES[user_id] -= payload_balance
            
            
            if user_id not in VOUCHERS:
                VOUCHERS[user_id] = 0
            VOUCHERS[user_id] += payload_balance
            
            
            return True
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

    def reject_proposal(payload):
        offer = Offer.getOffer(payload['id'])
        if not offer:
            return False

        offer.status = payload['status']  # refused
        offer.proposer_id = payload['proposer_id']
        Offer.updateOffer(payload['id'])

        return True

    def confirm_offer(offer_id):
        offer = Offer.getOffer(offer_id)
        if not offer:
            return False

        offer.ended = True
        offer.ended_at = datetime.datetime.now()
        Offer.updateOffer(offer_id, offer)

        return True

    def reoffer(payload):
        newOffer = Offer(len(OFFERS), payload["name"], payload["description"], payload["user_id"], payload['original_offer_id'],
                         payload["proposer_id"], payload["offer_value"], payload["image"], payload["status"], payload["ended"],
                         payload["created_at"], payload["ended_at"], payload["updated_at"], payload["country"], payload["state"], payload["city"],
                         payload["street"], payload["zipcode"], payload["number"], payload["complement"], payload["selectedType"], payload["productType"])
        Offer.createOffer(newOffer)

        return newOffer

    def offer_proposal(payload):
        newOffer = Offer(len(OFFERS), payload["name"], payload["description"], payload["user_id"], payload['original_offer_id'],
                         payload["proposer_id"], payload["offer_value"], payload["image"], payload["status"], payload["ended"],
                         payload["created_at"], payload["ended_at"], payload["updated_at"], payload["country"], payload["state"], payload["city"],
                         payload["street"], payload["zipcode"], payload["number"], payload["complement"], payload["selectedType"], payload["productType"])
        Offer.createOffer(newOffer)

        return newOffer

    def generate_mock_offers(num_offers):
        statuses = ['pending', 'reoffered', 'accepted']
        for i in range(num_offers):
            status = random.choice(statuses)
            offer_data = (i, f"Offer {i}", f"Description for Offer {i}", 1, 1000, 2, 50.0, None, status, False,
                          "2023-08-02 12:00:00", "2023-08-02 13:00:00", "2023-08-02 14:00:00", "Country", "State", "City",
                          "Street", "12345", "123", "10A", "1")
            offer_instance = Offer(*offer_data)
            OFFERS.append(offer_instance)

        return OFFERS


class Client:
    def __init__(self, id, name, account_number, balance):
        self.id = id
        self.name = name
        self.account_number = account_number
        self.balance = balance

    def create_client(data):
        newClient = Client(len(CLIENTS), data[0], data[1], data[2])
        CLIENTS.append(newClient)

        return True

    def addBalance(user_id, amount):
        client = Client.getClient(user_id)
        if not client:
            return False

        client.balance += amount
        CLIENTS[user_id] = client
        return True

    def getClient(id):
        client = CLIENTS[id]
        return client

    def getClients():
        for client in CLIENTS:
            logger.info("id: " + str(client.id))
            logger.info("Name: " + str(client.name))
            logger.info("Account number: " + str(client.account_number))
            logger.info("Balance: " + str(client.balance))
        return CLIENTS


def keccak(data):
    # Keccak constants
    r = (200 - 2 * 256)
    c = [[0 for i in range(5)] for j in range(5)]
    bits = 1600

    # Padding
    data += b'\x01'  # Padding 0x01
    data += b'\x00' * (-(len(data) + 1) % r)  # More 0x00 padding

    # Absorbing phase
    for i in range(0, len(data), r // 8):
        block = data[i:i + r // 8]
        for j in range(r // 8 // 8):
            c[j % 5][j // 5] ^= int.from_bytes(block[j * 8:(j + 1) * 8], 'big')

    # Squeezing phase
    output = b''
    while len(output) < bits // 8:
        for j in range(r // 8 // 8):
            output += c[j % 5][j // 5].to_bytes(8, 'big')
        c = keccak(c)
    return output[:bits // 8]

# Helper function to encode uint256 values
def encode_uint256(value):
    return value.to_bytes(32, byteorder='big')

# Helper function to encode address values
def encode_address(value):
    return bytes.fromhex(value[2:])  # Removing '0x' prefix

def get_balance(data):
    result = []
    for balance in BALANCES:
        if balance == data["user_id"]:
            result.append({"amount": BALANCES[balance], "type": "BALANCE"})
            break
    for voucher in VOUCHERS:
        if voucher == data["user_id"]:
            result.append({"amount": VOUCHERS[voucher], "type": "VOUCHER"})
            break
    return result or [{"amount": 0, "type": "BALANCE"}]


def add_balance(data):
    binary = bytes.fromhex(data)
    try:
        decoded = decode_packed(['address', 'uint256'], binary)
        user_id = decoded[0]
        amount = decoded[1]
        if user_id not in BALANCES:
            BALANCES[user_id] = 0
        BALANCES[user_id] += amount

    except Exception as e:
        msg = "Payload does not conform to ETHER deposit ABI"
        logger.error(f"{msg}\n{traceback.format_exc()}")
        return reject_input(msg, data["payload"])

    return 'accept'

def discount_balance(data):
    binary = bytes.fromhex(data)
    try:
        decoded = decode_packed(['address', 'uint256'], binary)
        user_id = decoded[0]
        amount = decoded[1]
        if user_id not in BALANCES:
            BALANCES[user_id] = 0
        BALANCES[user_id] -= amount

    except Exception as e:
        msg = "Payload does not conform to ETHER deposit ABI"
        logger.error(f"{msg}\n{traceback.format_exc()}")
        return reject_input(msg, data["payload"])

    return 'accept'


logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = "http://localhost:8080/host-runner" or environ["ROLLUP_HTTP_SERVER_URL"]

logger.info(f"HTTP rollup_server url is {rollup_server}")


def reject_input(msg, payload):
    logger.error(msg)
    response = requests.post(rollup_server + "/report",
                             json={"payload": payload})
    logger.info(
        f"Received report status {response.status_code} body {response.content}")
    return "reject"


def select_function_advance(payload):
    function_id = int(payload["function_id"])
    function_map = {
        0: lambda: Client.create_client(payload),
        1: lambda: Offer.offer_proposal(payload),
        2: lambda: Offer.accept_proposal(payload),
        3: lambda: Offer.reoffer(payload),
        4: lambda: Offer.generate_withdrawal(payload),
    }

    function = function_map.get(function_id)
    if function:
        return function()
    else:
        print("Function not found")


def select_function_inspect(payload):
    function_id = int(payload["function_id"])
    function_map = {
        0: Client.getClients,
        1: Offer.getOffersPending,
        2: Offer.getReOffers,
        3: Offer.getAllOffers,
        4: lambda: get_balance(payload),
    }

    function = function_map.get(function_id)
    if function:
        result = function()
        return result
    else:
        raise ValueError("Invalid function ID")


def hex2str(hex):
    """
    Decodes a hex string into a regular string
    """
    return bytes.fromhex(hex[2:]).decode("utf-8")


def str2hex(str):
    """
    Encodes a string as a hex string
    """
    return "0x" + str.encode("utf-8").hex()


def default(obj):
    if isinstance(obj, Offer):
        # Convert the Offer object to a dictionary
        offer_dict = {
            "id": obj.id,
            "name": obj.name,
            "description": obj.description,
            "user_id": obj.user_id,
            "proposer_id": obj.proposer_id,
            "offer_value": obj.offer_value,
            "original_offer_id": obj.original_offer_id,
            "value": obj.offer_value,
            "image": obj.image,
            "status": obj.status,
            "ended": obj.ended,
            "created_at": obj.created_at,
            "ended_at": obj.ended_at,
            "updated_at": obj.updated_at,
            "country": obj.country,
            "state": obj.state,
            "city": obj.city,
            "street": obj.street,
            "zipcode": obj.zipcode,
            "number": obj.number,
            "complement": obj.complement,
            "selectedType": obj.selectedType,
            "productType": obj.productType,
        }
        return offer_dict


def handle_advance(data):
    try:
        if data["metadata"]["msg_sender"].lower() == etherPortal['address'].lower():
            return add_balance(data["payload"][2:])
        decode = hex2str(data["payload"])
        payload = json.loads(decode)
        function_id = int(payload["function_id"])
        response = select_function_advance(payload)
        needToNotice = payload.get("needToNotice", False)
        enconde = str2hex(decode) if function_id == 2 else str2hex(
            json.dumps(default(response)))
        notice = {"payload": enconde}
        if needToNotice:
            response = requests.post(rollup_server + "/notice", json=notice)
            logger.info(
                f"Received notice status {response.status_code} body {response.content}")
        return "accept"
    except Exception as e:
        return "reject"


def handle_inspect(data):
    decode = hex2str(data["payload"])
    payload = json.loads(decode)
    response = select_function_inspect(payload)
    responseToString = '\n'.join([str(offer) for offer in response])
    enconde = str2hex(responseToString)
    report = {"payload": enconde}
    response = requests.post(rollup_server + "/report", json=report)
    logger.info(f"Received report status {response.status_code}")
    return "accept"


handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}

finish = {"status": "accept"}
rollup_address = None

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        logger.info(rollup_request["request_type"])
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])

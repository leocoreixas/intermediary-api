# Copyright 2022 Cartesi Pte. Ltd.
#
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use
# this file except in compliance with the License. You may obtain a copy of the
# License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from os import environ
import logging
import requests
import datetime
import json

CLIENTS = []
OFFERS = []
STATUS_CODES = [
    "accepted",
    "refused",
    "pending",
    "reoffered"
]


class Offer:
    def __init__(self, id, name, description, user_id, original_offer_id, proposer_id,
                 offer_value, image, status, ended, created_at, ended_at, updated_at,
                 country, state, city, street, zipcode, number, complement, selectedType):
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
        offer = Offer.getOffer(payload['id'])
        if not offer:
            return False
        Offer.updateOffer(payload['id'])
        Offer.updateOffer(payload['original_offer_id'])

        return True

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
                         payload["street"], payload["zipcode"], payload["number"], payload["complement"], payload["selectedType"])
        Offer.createOffer(newOffer)

        return newOffer

    def offer_proposal(payload):
        newOffer = Offer(len(OFFERS), payload["name"], payload["description"], payload["user_id"], payload['original_offer_id'],
                         payload["proposer_id"], payload["offer_value"], payload["image"], payload["status"], payload["ended"],
                         payload["created_at"], payload["ended_at"], payload["updated_at"], payload["country"], payload["state"], payload["city"],
                         payload["street"], payload["zipcode"], payload["number"], payload["complement"], payload["selectedType"])
        Offer.createOffer(newOffer)

        return newOffer


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


logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")


def select_function_advance(payload):
    function_id = int(payload["function_id"])
    logger.info("select_function_advance" + str(function_id))

    function_map = {
        0: lambda: Client.create_client(payload),
        1: lambda: Offer.offer_proposal(payload),
        2: lambda: Offer.accept_proposal(payload),
        3: lambda: Offer.reoffer(payload),
        # 4: lambda: Offer.reject_proposal(int(payload_obj["input_list"][0]), float(payload_obj["input_list"][1])),
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
        3: Offer.getAllOffers
        # 2: lambda: Client.getClient(int(inputFormat[1])),
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
        }
        return offer_dict


def handle_advance(data):  # geralmente dados persistente no blockchain
    decode = hex2str(data["payload"])
    payload = json.loads(decode)
    function_id = int(payload["function_id"])
    response = select_function_advance(payload)
    needToNotice = payload["needToNotice"]
    enconde = str2hex(decode) if function_id == 2 else str2hex(
        json.dumps(default(response)))
    notice = {"payload": enconde}
    if needToNotice:
        response = requests.post(rollup_server + "/notice", json=notice)
        logger.info(
            f"Received notice status {response.status_code} body {response.content}")
    return "accept"


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
        data = rollup_request["data"]
        if "metadata" in data:
            metadata = data["metadata"]
            if metadata["epoch_index"] == 0 and metadata["input_index"] == 0:
                rollup_address = metadata["msg_sender"]
                logger.info(f"Captured rollup address: {rollup_address}")
                continue
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])

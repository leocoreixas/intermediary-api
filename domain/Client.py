import Offer
import datetime

CLIENTS = []


class Client:
    def __init__(self, id, name, account_number, balance):
        self.id = id
        self.name = name
        self.account_number = account_number
        self.balance = balance

    def createClient(data):
        newClient = Client(data[0], data[1], data[2], data[3])
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

    def getClients(query):
        return CLIENTS

    def offer_proposal(user_id, offer_value):
        client = Client.getClient(user_id)
        if not client:
            return False

        newOffer = Offer(user_id, None, offer_value, "pending",
                         False, datetime.datetime.now(), None)
        Offer.createOffer(newOffer)
        
        return True

    

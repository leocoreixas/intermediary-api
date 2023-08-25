
import datetime
OFFERS = []


class Offer:
    def __init__(self, id, user_id, proposer_id, offer_value, status, ended, created_at, ended_at):
        self.id = id
        self.user_id = user_id
        self.proposer_id = proposer_id
        self.offer_value = offer_value
        self.status = status
        self.ended = ended
        self.created_at = created_at
        self.ended_at = ended_at
               
    def createOffer(data):
        OFFERS.append(data)
        return True
    
    def updateOffer(id, data):
        OFFERS[id] = data
        return True
    
    def getOffer(id):
        offer = OFFERS[id]
        return offer
    
    def getOffers(query):
        return OFFERS
        
    def accept_proposal(offer_id, proposer_id):
        offer = Offer.getOffer(offer_id)
        if not offer:
            return False

        offer.status = "accepted"
        offer.proposer_id = proposer_id
        Offer.updateOffer(offer_id, offer)
        
        return True

    def reject_proposal(offer_id, proposer_id):
        offer = Offer.getOffer(offer_id)
        if not offer:
            return False

        offer.status = "refused"
        offer.proposer_id = proposer_id
        Offer.updateOffer(offer_id, offer)

        return True

    def confirm_offer(offer_id):
        offer = Offer.getOffer(offer_id)
        if not offer:
            return False

        offer.ended = True
        offer.ended_at = datetime.datetime.now()
        Offer.updateOffer(offer_id, offer)

        return True
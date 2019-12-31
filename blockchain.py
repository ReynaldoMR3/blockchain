#Importing the libraries and modules needed.
import sys
import hashlib
import json
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
import requests
from urllib.parse import urlparse


#Declaring the class named blockchain.
class Blockchain(object):

    #dificulty level inside the block.
    difficulty_target = "0000"

    def hash_block(self, block):
        '''
        Encodes a block into array of bytes and then hashes it,
        you need to ensure that the dictionary is sorted, or
        you'll have inconsistent hashes in the future.
        '''
        block_encoded = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_encoded).hexdigest()


    #CLass constructor, stores the entire blockchain as a list.
    def __init__(self):
        self.nodes = set()

        #stores all the blocks in the entire blockchain.
        self.chain = []

        #temporarily stores the transactions for the current block.
        self.current_transactions = []

        '''
        create the genesis block with a specific fixed hash of
        previous block genesis block starsts with index 0
        '''
        genesis_hash = self.hash_block('genesis_block')
        self.append_block(
            hash_of_previous_block = genesis_hash,
            nonce = self.proof_of_work(0, genesis_hash, [])
        )


    def proof_of_work(self, index, hash_of_previous_block, transactions):
        '''
        Returns a nonce that will result in a hash that matches the
        difficulty target when the content of the current block is
        hashed. Increases the nonce until it finds the correct nonce
        to match the difficulty level.
        '''
        nonce = 0

        #Try hashing the nonce together with the hash of the previous block.
        while self.valid_proof(index, hash_of_previous_block,
            transactions, nonce) is False:
            nonce += 1

        return nonce

    # check if the block's hash meets the difficulty target
    def valid_proof(self, index, hash_of_previous_block,
        transactions, nonce):
        '''
        Create a string containing the hash of the previous block
        and the block content, including the nonce.
        '''
        content = f'{index}{hash_of_previous_block}{transactions}{nonce}'.encode()

        #hash using sha256
        content_hash = hashlib.sha256(content).hexdigest()

        #check if the hash meets the difficulty target.
        return content_hash[:len(self.difficulty_target)] == self.difficulty_target

    #creates a new block and adds it to the blockchain.
    def append_block(self, nonce, hash_of_previous_block):
        block = {
            'index': len(self.chain),
            'timestamp': time(),
            'transactions': self.current_transactions,
            'nonce': nonce,
            'hash_of_previous_block': hash_of_previous_block
        }
        # reset the current list of transactions
        self.current_transactions = []

        # add the new block to the blockchain.
        self.chain.append(block)
        return block


    #Adding trnasactions will add to the BLockchain class in the method:
    def add_transaction(self, sender, recipient, amount):
        '''
        This method adds a new transaction to the current list of transactions.
        It then gets the index of the last block in the blockchain and adds
        one to it. This new index will be the block that the current transaction
        will be added to.
        '''
        self.current_transactions.append({
            'amount': amount,
            'recipient': recipient,
            'sender': sender,
        })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        #returns the last block in the blockchain.
        return self.chain[-1]

    # add a new node to the list of nodes eg. "http://192.169.1.2:500"
    def add_node(self, address):
        '''
        Allows a new node to be added to the nodes member,
        for example, if "http://...1.2:500" is passed to the method,
        the IP address and port number "http://...23:500" will be added
        to the nodes member.
        '''
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
        print(parsed_url.netloc)


    #determine if a given blockchain is valid
    def valid_chain():
        '''
        Validates that a given blockchain is valid by performing
        the following checks:
            It goes through each block in the blockchain and hashes
            each block and verifies that the hash of each block is correctly
            recorded in  the next block.

            It verifies that the nonce in each block is valid.
        '''
        last_block = chain[0]   #the genesis block
        current_index = 1    #starts with the second block

        while current_index < len(chain):
            block = chain[current_index]
            if block['hash_of_previous_block'] != self.hash_block(last_block):
                return False

            #check for valid nonce
            if not self.valid_proof(
                current_index,
                block['hash_of_previous_block'],
                block['transactions'],
                block['nonce']):
                return False

            # move on to the next block on the chain
            last_block = block
            current_index += 1

        #The chain is valid
        return True


    #Update blockchain
    def update_blockchain(self):
        '''
        Checks that the blockchain from neighboring nodes is valid and
        that the node with the longest valid chain is the authoritative one; if
        another node with valid blockchain is longer than the current one,
        it will replace the current blockchain.
        '''
        #get the nodes around us that has been registered
        neighbours = self.nodes
        new_chain = None

        #for simplicity, look for chains longer than ours.
        max_length = len(self.chain)

        #grab and verify the chains from all the nodes in our network
        for node in neighbours:
            #get the blockchain from the other nodes.
            response = requests.get(f'http://{node}/blockchain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

            #Check if the lenght is longer and the chain is valid.
            if lenght > max_length and self.valid_chain(chain):
                max_length = lenght
                new_chain = chain

        #replace our chain if we discover a new, valid chain longer than ours.
        if new_chain:
            self.chain = new_chain
            return True

        return False


#Exposing the blockchain class as a REST API.
app = Flask (__name__)

#generate a globally unique address for this node.
node_identifier = str(uuid4()).replace('-', '')

#instantiate the BLockchain
blockchain = Blockchain()

#Obtaining the full BLockchain
#return the entire blockchain.
@app.route('/blockchain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


#Performing Mining
@app.route('/mine', methods=['GET'])
def mine_block():
    '''
    The miner must receive a reward for finding the proof
    the sender is "0" to signify that this node has mined a
    new coin
    '''
    blockchain.add_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )
    # obtain the hash of last block in the blockchain.
    last_block_hash = blockchain.hash_block(blockchain.last_block)

    # using PoW, get the nonce for the new block to be added to the blockchain.
    index = len(blockchain.chain)
    nonce = blockchain.proof_of_work(index, last_block_hash,
            blockchain.current_transactions)

    # add the new block to the blockchain using the last block, hash and the current nonce.
    block = blockchain.append_block(nonce, last_block_hash)
    response = {
        'message': 'New Block Mined',
        'index': block['index'],
        'hash_of_previous_block': block['hash_of_previous_block'],
        'nonce': block['nonce'],
        'transactions': block['transactions'],
    }
    return jsonify(response), 200


#Adding transtactions
@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    # get the value passed in from the client
    values = request.get_json()

    # check that the required fields are in the POST'ed data
    required_fields = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required_fields):
        return ('Missing fields', 400)

    # create a new transaction
    index = blockchain.add_transaction(
        values['sender'],
        values['recipient'],
        values['amount']
    )

    response = {'message':
        f'Transaction will be added to Block{index}'}
    return (jsonify(response), 201)


@app.route('/nodes/add_nodes', methods=['POST'])
def add_nodes():
    #get the nodes passed in from the client
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Missing node(s) info", 400

    for node in nodes:
        blockchain.add_node(node)

    response = {
        'message': 'New nodes added',
        'nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/sync', methods=['GET'])
def sync():
    updated = blockchain.update_blockchain()
    if updated:
        response = {'message': 'The blockchain has been updated to the latest',
                    'blockchain': blockchain.chain}
    else:
        response= {'message': 'Our blockchain is the latest',
                    'blockchain': blockchain.chain}

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(sys.argv[1]))

'''Voter Server'''
from ServerGeneric import GenericHandler
from ServerGeneric import GenericServer
from ServerGeneric import getTCPSocketServer
import ServerConfiguration as SC##information about network
import threading
from ServerController import json_client
from ServerController import parse_request_json
from ServerController import send_response_json
import json
import sv_election

class VoterServer(GenericServer):
    # TODO election logic should be moved to other files like Voter.py
    def __init__(self, server_address, RequestHandlerClass, election_parameters):
        GenericServer.__init__(self, server_address, RequestHandlerClass)
        self.election = sv_election.Election(election_parameters)
        
    def produce_votes(self):
        """ Produces votes """
        # Vote !
        for voter in self.election.voters:
            for race in self.election.races:
                voter.cast_vote(race) # it populates self.election.cast_votes'''
        
    def post_voter_receipts(self):
        """ Post all voter receipts on the SBB. """
        receipts = dict()
        for voter in self.election.voters:
            for ballot_id in voter.receipts:
                receipts[ballot_id] = voter.receipts[ballot_id]
        self.ask_sbb_to_post("casting:receipts",
                      {"receipt_dict": receipts},
                      time_stamp=False)
                      
    def distribute_votes(self):
        """ Distribute cast votes among MixServers """
        for race_id in self.election.race_ids:
            for px in self.election.p_list:
                for i in self.election.server.row_list:
                    vote = self.election.cast_votes[race_id][px][i]
                    # save these values in our server data structures
                    # in a non-simulated real election, this would be done
                    # by communicating securely from voter (or tablet) to the
                    # first column of servers.
                    sdbp = self.election.server.sdb[race_id][i][0]
                    sdbp['ballot_id'][px] = vote['ballot_id']
                    sdbp['x'][px] = vote['x']
                    sdbp['u'][px] = vote['u']
                    sdbp['v'][px] = vote['v']
                    sdbp['ru'][px] = vote['ru']
                    sdbp['rv'][px] = vote['rv']
                    sdbp['cu'][px] = vote['cu']
                    sdbp['cv'][px] = vote['cv']
        # distribute votes to mix servers
        for race_id in self.election.race_ids:
            for i in self.election.server.row_list:
                sdbp = self.election.server.sdb[race_id][i][0]
                for s in self.servers_alive[SC.ROLE_MIX]:
                    response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_SPLIT_VALUE_VOTES, body = (race_id, i, sdbp), origin = (self.server_address[0], self.server_address[1]), auth = "")

    def post_cast_vote_commitments(self):
        """ Post cast vote commitments onto SBB. """
        pass
        cvs = self.election.cast_votes
        cvcs = dict()
        for race_id in self.election.race_ids:
            cvcs[race_id] = dict()
            for px in self.election.p_list:
                cvcs[race_id][px] = dict()
                for i in self.election.server.row_list:
                    cvcs[race_id][px][i] = dict()
                    cvcs[race_id][px][i]['ballot_id'] = cvs[race_id][px][i]['ballot_id']
                    cvcs[race_id][px][i]['cu'] = cvs[race_id][px][i]['cu']
                    cvcs[race_id][px][i]['cv'] = cvs[race_id][px][i]['cv']
        self.ask_sbb_to_post("casting:votes", 
                      {"cast_vote_dict": cvcs},
                      time_stamp=False)

class VoterHandler(GenericHandler):
    '''
    The RequestHandler class for our server. It is instantiated once per connection to the server.    
    '''

    def handle(self):
        """ ServerX -> Controller [Any request]
        Parse message and handle it depending on origin and phase.
        """
        request_data = parse_request_json(self.request)
        response = None
        if request_data[SC.MSG_TITLE] == SC.MESSAGE_GET_ROLE:
            response = self.handle_get_role(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_BROADCAST_ROLES:
            response = self.handle_get_network_information(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_PRODUCE_VOTES:
            response = self.handle_produce_votes(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_DISTRIBUTE_VOTES:
            response = self.handle_distribute_votes(request_data)
        else:
            response = self.handle_unexpected_request()
        send_response_json(self.request, response, request_data[SC.MSG_ORIGIN])

    def handle_produce_votes(self, request_data):
        """ Controller -> Voter [Produce Votes]
        Input: Election Information (races, number of votes)
        Action: Run simulation for vote casting, ask
        Output: Done """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        self.server.produce_votes()
        self.server.post_voter_receipts()
        response[SC.MSG_BODY] = "Done"
        return response

    def handle_distribute_votes(self, request_data):
        """ Controller -> Voter [Distribute Votes]
        Input: Election Information (races, number of votes)
        Action: Run simulation for vote casting, ask
        Output: Done """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        self.server.distribute_votes()
        self.server.post_cast_vote_commitments()
        response[SC.MSG_BODY] = "Done"
        return response

if __name__ == "__main__":
    response = json_client(ip = SC.CONTROLLER_HOST, port = SC.CONTROLLER_PORT, title = SC.MESSAGE_PING_CONTROLLER_1, body = "" , origin = "", auth = "")
    ip, port = response[SC.MSG_BODY]
    # Create the server, binding to the same ip address
    server, server_addr = getTCPSocketServer(Handler = GenericHandler, addr = (ip, port))
    # Let Controller know to which address server is listening to
    response = json_client(ip = SC.CONTROLLER_HOST, port = SC.CONTROLLER_PORT, title = SC.MESSAGE_PING_CONTROLLER_2, body = SC.ROLE_VOTER, origin = server_addr, auth = "")
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server_thread = threading.Thread(target=server.serve_forever, daemon = True)
    #daemon threads allow us to finish the program execution, even though some threads may be running
    server_thread.start()
    stop = input("Stop?")
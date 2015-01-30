'''SBB Server'''
from ServerGeneric import GenericHandler
from ServerGeneric import GenericServer
from ServerGeneric import getTCPSocketServer
import ServerConfiguration as SC##information about network
import threading
from ServerController import json_client
from ServerController import parse_request_json
from ServerController import send_response_json
import json
import sv_sbb
import sv_election
import sv

"""
TODO Vote Production
-try to remove number_of_voters from SBB, Election
-in voters cast arranged by race. Maybe arrange by voter (because of chronological order).
-"casting:votes" does not need to have signatures, they are verified by the voter, via hash

TODO Secure Communications
-missing the keys for the poster, who is allowed to post and what pk’s are
-Goal: adding digital signatures is going to increase file size by 1%
-Most important signatures: initialization (election) who is allowed, 
-other communications, MAC are simpler no need for digital signatures.
-We need to do a documentation of the SBB - very carefully to allow other verifiers.
"""

class SBBServer(GenericServer):
    def __init__(self, server_address, RequestHandlerClass, election_parameters):
        GenericServer.__init__(self, server_address, RequestHandlerClass)
        self.election = sv_election.Election(election_parameters)
        self.sbb = sv_sbb.SBB(self.election.election_id)

    def create_sbb(self, election_id):
        self.sbb = sv_sbb.SBB(self.election.election_id)        

class SBBHandler(GenericHandler):
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
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_POST_TO_SBB:
            response = self.handle_post(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_PRINT_SBB:
            response = self.handle_print_sbb(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_HASH_SBB:
            response = self.handle_hash_sbb(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_CLOSE_SBB:
            response = self.handle_close_sbb(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_VERIFY:
            response = self.handle_verify_sbb(request_data)
        else:
            response = self.handle_unexpected_request()
        send_response_json(self.request, response, request_data[SC.MSG_ORIGIN])

    def handle_post(self, request_data):
        """ServerX -> SBB[Post Y]
        Input: Y
        Action: Post to PBB (in memory)
        Output: Done"""
        msg_header, msg_dict, time_stamp = request_data[SC.MSG_BODY]
        print("POSTING ", request_data[SC.MSG_TITLE])
        #print("POSTING ", request_data)
        self.server.sbb.post(msg_header, msg_dict, time_stamp)
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = "Done"
        return response

    def handle_print_sbb(self, request_data):
        """ServerX -> SBB[Print SBB to disk]
        Input: public_flag, sbb_filename
        Action: Print SBB file to disk
        Output: Done"""
        public, sbb_filename = request_data[SC.MSG_BODY]
        print("PRINTING ", request_data)
        self.server.sbb.print_sbb(public, sbb_filename)
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = "Done"
        return response

    def handle_hash_sbb(self, request_data):
        """ServerX -> SBB[Compute hash of SBB]
        Input: public_flag
        Action: Compute hash of SBB
        Output: sbb_hash"""
        public = request_data[SC.MSG_BODY]
        sbb_hash = self.server.sbb.hash_sbb(public)
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = sv.bytes2hex(sbb_hash)
        print ("response[SC.MSG_BODY]/hash: ", response[SC.MSG_BODY])
        return response
    
    def handle_close_sbb(self, request_data):
        """ServerX -> SBB[Close SBB]
        Input: Request to close SBB
        Action: Close SBB (set flag)
        Output: Done"""
        self.server.sbb.close()
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = "Done"
        return response
    
    def handle_verify_sbb(self, request_data):
        """ServerX -> SBB[Verify SBB]
        Input: Request to verify SBB, sbb_filename
        Action: Verify SBB
        Output: Done"""
        import sv_verifier
        sbb_filename = request_data[SC.MSG_BODY]
        sv_verifier.verify(sbb_filename)
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = "Done"
        return response

if __name__ == "__main__":
    response = json_client(ip = SC.CONTROLLER_HOST, port = SC.CONTROLLER_PORT, title = SC.MESSAGE_PING_CONTROLLER_1, body = "" , origin = "", auth = "")
    ip, port = response[SC.MSG_BODY]
    # Create the server, binding to the same ip address
    server, server_addr = getTCPSocketServer(Handler = GenericHandler, addr = (ip, port))
    # Let Controller know to which address server is listening to
    response = json_client(ip = SC.CONTROLLER_HOST, port = SC.CONTROLLER_PORT, title = SC.MESSAGE_PING_CONTROLLER_2, body = SC.ROLE_SBB, origin = server_addr, auth = "")
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server_thread = threading.Thread(target=server.serve_forever, daemon = True)
    #daemon threads allow us to finish the program execution, even though some threads may be running
    server_thread.start()
    stop = input("Stop?")
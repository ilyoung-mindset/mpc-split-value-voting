'''Generic Server'''
import socketserver
import ServerConfiguration as SC##information about network
import threading
from ServerController import json_client
from ServerController import parse_request_json
from ServerController import send_response_json
import json
import sv_election

class GenericServer(socketserver.TCPServer):
    """ Here we keep any relevant states for our server """
    def __init__(self, server_address, RequestHandlerClass):
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)
        self.servers_alive = {SC.ROLE_GENERIC: [], SC.ROLE_VOTER: [], SC.ROLE_CONTROLLER: [], SC.ROLE_SBB: [], SC.ROLE_MIX: []}
        self.role = SC.ROLE_GENERIC
        self.role_index = -1

    def add_election_info(self, election_parameters):
        self.election = sv_election.Election(election_parameters)

    def record_servers_alive(self, servers_alive):
        self.servers_alive = servers_alive
        print("self.servers_alive", self.servers_alive)
        self.role_index = self.servers_alive[self.role].index([self.server_address[0], self.server_address[1]])
        print("self.role_index", self.role_index)
    
    def ask_sbb_to_post(self, msg_header, msg_dict=None, time_stamp=True):
        for s in self.servers_alive[SC.ROLE_SBB]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_POST_TO_SBB, body = (msg_header, msg_dict, time_stamp), origin = (self.server_address[0], self.server_address[1]), auth = "")
    
    def ask_sbb_hash(self, public=True):
        for s in self.servers_alive[SC.ROLE_SBB]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_HASH_SBB, body = public, origin = (self.server_address[0], self.server_address[1]), auth = "")
        return response[SC.MSG_BODY]

class GenericHandler(socketserver.BaseRequestHandler):
    '''
    The RequestHandler class for our server. It is instantiated once per connection to the server.
    '''
    
    def handle(self):
        """ ServerX -> Generic [Any request]
        Parse message and handle it depending on origin and phase.
        """
        print("Generic Server Handler being executed")
        request_data = parse_request_json(self.request)
        if request_data[SC.MSG_TITLE] in [SC.MESSAGE_ASSIGN_ROLE_VOTER, SC.MESSAGE_ASSIGN_ROLE_SBB, SC.MESSAGE_ASSIGN_ROLE_MIX]:
            response = self.handle_assign_role(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_GET_ROLE:
            response = self.handle_get_role(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_BROADCAST_ROLES:
            response = self.handle_get_network_information(request_data)
        else:
            response = self.handle_unexpected_request(request_data)
        send_response_json(self.request, response, request_data[SC.MSG_ORIGIN])

    def get_incomplete_response(self, title):
        response = {}
        response[SC.MSG_TITLE] = title
        response[SC.MSG_ORIGIN] = self.server.server_address #(ip, port)
        response[SC.MSG_AUTH] = "" # TODO add public key and digital signature info here
        return response        
    
    def handle_assign_role(self, request_data):
        """ Controller -> Generic [Initializing Roles]
        Input: Role information
        Action: Each server runs an initialization routine
        Output: Any required public info (like a public key or digital signature)
        """
        server_addr = ("","")
        initialization_param = request_data[SC.MSG_BODY]
        if request_data[SC.MSG_TITLE] == SC.MESSAGE_ASSIGN_ROLE_VOTER:
            from ServerVoter import VoterHandler
            from ServerVoter import VoterServer
            # Initializing voter server
            self.server.__class__ = VoterServer
            self.server.RequestHandlerClass = VoterHandler
            self.server.add_election_info(initialization_param)
            voter_server = self.server
            voter_server_addr = self.server.server_address
            #voter_server, voter_server_addr = getTCPSocketServer(Handler = VoterHandler, ServerConstructor = VoterServer, addr = self.server.server_address ,initialization_param = initialization_param)
            voter_server_t = threading.Thread(target=voter_server.serve_forever, daemon = True)
            voter_server.role = SC.ROLE_VOTER
            voter_server_t.start()
            server_addr = voter_server_addr
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_ASSIGN_ROLE_SBB:
            from ServerSBB import SBBHandler
            from ServerSBB import SBBServer
            # Initializing SBB server
            self.server.__class__ = SBBServer
            self.server.RequestHandlerClass = SBBHandler
            self.server.add_election_info(initialization_param)
            self.server.create_sbb(self.server.election.election_id)
            sbb_server = self.server
            sbb_server_addr = self.server.server_address
            #sbb_server, sbb_server_addr = getTCPSocketServer(Handler = SBBHandler, ServerConstructor = SBBServer, addr = self.server.server_address ,initialization_param = initialization_param)
            sbb_server_t = threading.Thread(target=sbb_server.serve_forever, daemon = True)
            sbb_server.role = SC.ROLE_SBB
            sbb_server_t.start()
            server_addr = sbb_server_addr
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_ASSIGN_ROLE_MIX:
            from ServerMix import MixHandler
            from ServerMix import MixServer
            # Initializing Mix server
            self.server.__class__ = MixServer
            self.server.RequestHandlerClass = MixHandler
            self.server.add_election_info(initialization_param)
            mix_server = self.server
            mix_server_addr = self.server.server_address
            #mix_server, mix_server_addr = getTCPSocketServer(Handler = MixHandler, ServerConstructor = MixServer, addr = self.server.server_address ,initialization_param = initialization_param)
            mix_server_t = threading.Thread(target=mix_server.serve_forever, daemon = True)
            mix_server.role = SC.ROLE_MIX
            mix_server_t.start()
            server_addr = mix_server_addr
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = server_addr
        return response
        
    def handle_get_role(self, request_data):
        """ ServerX -> Server [Get role message]
        Input: None
        Action: None
        Output: Server role """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = self.server.role
        return response

    def handle_get_network_information(self, request_data):
        """Controller -> ServerX [Network Info]
        Input: Everyone’s role and their respective public info.
        Action: Record who is network info
        Output: Done"""
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        servers_alive = request_data[SC.MSG_BODY]
        self.server.record_servers_alive(servers_alive)
        response[SC.MSG_BODY] = "Done"
        return response
    
    def handle_unexpected_request(self, request_data):
        """ ServerX -> Controller [Unexpected Message]
        Input: None
        Action: None
        Output: 'Message not expected' """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = "Message not expected"
        return response

def getTCPSocketServer(Handler, addr, ServerConstructor = GenericServer, initialization_param = None):
    #TODO handle error case
    ip, port = addr
    server = None
    port = 1998
    while True:
        try:
            if initialization_param == None:
                server = ServerConstructor((ip, port), Handler)
            else:
                server = ServerConstructor((ip, port), Handler, initialization_param)
            break
        except ConnectionRefusedError:
            print("ConnectionRefusedError with (ip, port):", (ip, port))
        except OSError:
            print("OSError with (ip, port):", (ip, port))
        port += 1
    server_addr = (ip, port)
    return (server, server_addr)

if __name__ == "__main__":
    response = json_client(ip = SC.CONTROLLER_HOST, port = SC.CONTROLLER_PORT, title = SC.MESSAGE_PING_CONTROLLER_1, body = "" , origin = "", auth = "")
    ip, port = response[SC.MSG_BODY]
    # Create the server, binding to the same ip address
    server, server_addr = getTCPSocketServer(Handler = GenericHandler, addr = (ip, port))
    # Let Controller know to which address server is listening to
    response = json_client(ip = SC.CONTROLLER_HOST, port = SC.CONTROLLER_PORT, title = SC.MESSAGE_PING_CONTROLLER_2, body = "", origin = server_addr, auth = "")
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server_thread = threading.Thread(target=server.serve_forever, daemon = True)
    #daemon threads allow us to finish the program execution, even though some threads may be running
    server_thread.start()
    stop = input("Stop?")
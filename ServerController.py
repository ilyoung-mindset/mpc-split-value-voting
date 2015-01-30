''' Controller - responsible for initializing and coordinating other servers
    ControllerServer keeps the relevant state information
    ControllerHandler handles the incoming requests from other servers

    Request and response messages consist of title, body, origin and authorization
    Messages are exchanged using the JSON format
    Consult ServerConfiguration.py for more details on initialization parameters

    TODO: modify code, so that Controller learn about all errors and keep a log file,
    right now we need to need to look at each Servers log that is being printed 
'''
import socketserver
import ServerConfiguration as SC##information about network
import threading
import socket
import sys
import time
import json

class ControllerServer(socketserver.TCPServer):
    """ Here we keep any relevant states for our server """

    def __init__(self, server_address, RequestHandlerClass):
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)
        self.servers_alive = {SC.ROLE_GENERIC: [], SC.ROLE_VOTER: [], SC.ROLE_CONTROLLER: [], SC.ROLE_SBB: [], SC.ROLE_MIX: [],
                            SC.ROLE_VOTER+"_PENDING": [], SC.ROLE_SBB+"_PENDING": [], SC.ROLE_MIX+"_PENDING": []}
        self.role = SC.ROLE_CONTROLLER

    def wait_for_servers(self, num_servers_per_role):
        n = sum([len(l) for l in self.servers_alive.values()]) # total number of servers alive
        target_n = sum(list(num_servers_per_role.values()))
        while n < target_n:
            time.sleep(1)
            print("num servers_alive", n, "target num servers_alive", target_n)
            print("self.servers_alive", self.servers_alive)
            n = sum([len(l) for l in self.servers_alive.values()]) # total number of servers alive
    
    def assign_server_roles(self, num_servers_per_role, initialization_params_per_role):
        while len(self.servers_alive[SC.ROLE_VOTER]) < num_servers_per_role[SC.ROLE_VOTER]:
            # if pending list not empty get it from there otherwise get it from generic
            s = None
            assert len(self.servers_alive[SC.ROLE_VOTER + "_PENDING"]) + len(self.servers_alive[SC.ROLE_GENERIC]) > 0, "Incorrect Number of Servers" + str(num_servers_per_role)
            if len(self.servers_alive[SC.ROLE_VOTER + "_PENDING"]) > 0:
                s = self.servers_alive[SC.ROLE_VOTER + "_PENDING"].pop()
            else: # len(self.servers_alive[SC.ROLE_GENERIC]) > 0:
                s = self.servers_alive[SC.ROLE_GENERIC].pop()
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_ASSIGN_ROLE_VOTER, body = initialization_params_per_role[SC.ROLE_VOTER], origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
            server_addr = response[SC.MSG_BODY]
            print("Server ", str(server_addr), " recorded as SC.ROLE_VOTER")
            self.servers_alive[SC.ROLE_VOTER].append(server_addr)
        while len(self.servers_alive[SC.ROLE_SBB]) < num_servers_per_role[SC.ROLE_SBB]:
            # if pending list not empty get it from there otherwise get it from generic
            s = None
            assert len(self.servers_alive[SC.ROLE_SBB + "_PENDING"]) + len(self.servers_alive[SC.ROLE_GENERIC]) > 0, "Incorrect Number of Servers" + str(num_servers_per_role)
            if len(self.servers_alive[SC.ROLE_SBB + "_PENDING"]) > 0:
                s = self.servers_alive[SC.ROLE_SBB + "_PENDING"].pop()
            else: # len(self.servers_alive[SC.ROLE_GENERIC]) > 0:
                s = self.servers_alive[SC.ROLE_GENERIC].pop()
            ip, port = s
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_ASSIGN_ROLE_SBB, body = initialization_params_per_role[SC.ROLE_SBB], origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
            server_addr = response[SC.MSG_BODY]
            print("Server ", str(server_addr), " recorded as SC.ROLE_SBB")
            self.servers_alive[SC.ROLE_SBB].append(server_addr)
        while len(self.servers_alive[SC.ROLE_MIX]) < num_servers_per_role[SC.ROLE_MIX]:
            # if pending list not empty get it from there otherwise get it from generic
            s = None
            assert len(self.servers_alive[SC.ROLE_MIX + "_PENDING"]) + len(self.servers_alive[SC.ROLE_GENERIC]) > 0, "Incorrect Number of Servers" + str(num_servers_per_role)
            if len(self.servers_alive[SC.ROLE_MIX + "_PENDING"]) > 0:
                s = self.servers_alive[SC.ROLE_MIX + "_PENDING"].pop()
            else: # len(self.servers_alive[SC.ROLE_GENERIC]) > 0:
                s = self.servers_alive[SC.ROLE_GENERIC].pop()
            ip, port = s
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_ASSIGN_ROLE_MIX, body = initialization_params_per_role[SC.ROLE_MIX], origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
            server_addr = response[SC.MSG_BODY]
            print("Server ", str(server_addr), " recorded as SC.ROLE_MIX")
            self.servers_alive[SC.ROLE_MIX].append(server_addr)

    def test_assigned_server_roles(self):
        ''' Testing assigned servers '''
        for s in self.servers_alive[SC.ROLE_VOTER]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_GET_ROLE, body = "", origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
            assert response[SC.MSG_BODY] == SC.ROLE_VOTER, "response[SC.MSG_BODY]" + response[SC.MSG_BODY]
        for s in self.servers_alive[SC.ROLE_SBB]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_GET_ROLE, body = "", origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
            assert response[SC.MSG_BODY] == SC.ROLE_SBB
        for s in self.servers_alive[SC.ROLE_MIX]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_GET_ROLE, body = "", origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
            assert response[SC.MSG_BODY] == SC.ROLE_MIX
        # all initializations happened correctly
        
    def broadcast_network(self):
        ''' Broadcast information about all servers to everyone '''
        for roles in self.servers_alive:  # I can parallelize this loop
            for s in self.servers_alive[roles]:
                response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_BROADCAST_ROLES, body = self.servers_alive, origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")

    def ask_to_produce_votes(self, election_info):
        ''' Ask voter servers to produce votes '''
        for s in self.servers_alive[SC.ROLE_VOTER]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_PRODUCE_VOTES, body = election_info, origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")

    def ask_voters_to_distribute_votes(self):
        ''' Ask voter servers to produce votes '''
        for s in self.servers_alive[SC.ROLE_VOTER]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_DISTRIBUTE_VOTES, body = "", origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")

    def ask_sbb_to_post(self, msg_header, msg_dict=None, time_stamp=True):
        for s in self.servers_alive[SC.ROLE_SBB]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_POST_TO_SBB, body = (msg_header, msg_dict, time_stamp), origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")

    def ask_sbb_to_print(self, public = True, sbb_filename = None):
        for s in self.servers_alive[SC.ROLE_SBB]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_PRINT_SBB, body = (public, sbb_filename), origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
    
    def ask_mixservers_to_mix(self):
        ''' The ServerController abstract the phases, but it provides a counter to help with synchronization '''
        phase = 0
        continue_flag = True
        while continue_flag:
            continue_flag = False
            for s in self.servers_alive[SC.ROLE_MIX]:
                response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_MIX, body = phase, origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
                if response[SC.MSG_BODY] != "Done":
                    continue_flag = True
            phase += 1

    def ask_mixservers_for_proofs(self):
        ''' The ServerController abstract the phases, but it provides a counter to help with synchronization '''
        phase = 0
        continue_flag = True
        while continue_flag:
            continue_flag = False
            for s in self.servers_alive[SC.ROLE_MIX]:
                response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_PROVE, body = phase, origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")
                if response[SC.MSG_BODY] != "Done":
                    continue_flag = True
            phase += 1

    def ask_mixservers_for_tally(self):
        for s in self.servers_alive[SC.ROLE_MIX]:
            # only last column computes tally, only one post it to SBB
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_TALLY, body = "", origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")

    def ask_sbb_to_close(self):
        for s in self.servers_alive[SC.ROLE_SBB]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_CLOSE_SBB, body = "", origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")

    def ask_sbb_to_verify(self, sbb_filename):
        for s in self.servers_alive[SC.ROLE_SBB]:
            response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_VERIFY, body = sbb_filename, origin = (SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), auth = "")

class ControllerHandler(socketserver.BaseRequestHandler):
    '''
    The RequestHandler class for our server. It is instantiated once per connection to the server.
    '''
    def handle(self):
        """ ServerX -> Controller [Any request]
        Parse message and handle it depending on origin and phase.
        """
        request_data = parse_request_json(self.request)
        if request_data[SC.MSG_TITLE].startswith(SC.MESSAGE_PING_CONTROLLER_1):
            response = self.handle_provide_client_address(request_data)
        elif request_data[SC.MSG_TITLE].startswith(SC.MESSAGE_PING_CONTROLLER_2):
            response = self.handle_generic_ping(request_data)
        else:
            response = self.handle_unexpected_request(request_data)
        send_response_json(self.request, response, request_data[SC.MSG_ORIGIN])

    def handle_provide_client_address(self, request_data):
        """ Generic -> Controller [Ping]
        Input: None
        Action: None
        Output: Client address"""
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = (self.client_address[0], self.client_address[1])
        return response

    def handle_generic_ping(self, request_data):
        """ Generic -> Controller [Ping]
        Input: Server Address
        Action: Record who is alive
        Output: Done"""
        #origin = request_data['origin']
        origin = request_data[SC.MSG_ORIGIN]
        role = request_data[SC.MSG_BODY]
        if role != "" and role in SC.ROLES_LIST:
            self.server.servers_alive[role+"_PENDING"].append((origin[0], origin[1]))
        else:
            self.server.servers_alive[SC.ROLE_GENERIC].append((origin[0], origin[1]))
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response_str = "Server " + str(origin) + " recorded as SC.ROLE_GENERIC"
        response[SC.MSG_BODY] = response_str
        return response
        
    def handle_unexpected_request(self, request_data):
        """ ServerX -> Controller [Unexpected Message]
        Input: None
        Action: None
        Output: 'Message not expected' """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        response[SC.MSG_BODY] = "Message not expected"
        return response

    def get_incomplete_response(self, title):
        response = {}
        response[SC.MSG_TITLE] = title
        response[SC.MSG_ORIGIN] = self.server.server_address #(ip, port)
        response[SC.MSG_AUTH] = "" # TODO add public key and digital signature info here
        return response   

####################################################################################
# TODO move code below to utils
# TODO handle messages larger than SC.MSG_BUFFER_SIZE

import sv

data_transferred_size = 0 # for debugging purposes

def json_client(ip, port, title, origin, body = "empty body", auth = "empty auth"):
    message = {SC.MSG_TITLE: title, SC.MSG_BODY: body , SC.MSG_ORIGIN: origin, SC.MSG_AUTH: auth}
    global data_transferred_size
    data_transferred_size += get_size(message)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if ip == "":
        ip = "127.0.0.1"
    destination_str = str([ip, port])
    print("--->" + destination_str)
    print("\t" + SC.MSG_TITLE + ": " + str(message[SC.MSG_TITLE]))
    #print("\t" + SC.MSG_BODY + ": " + str(message[SC.MSG_BODY]))
    while True:
        if s.connect_ex((ip, port)):
            print("Connection Refused Error, trying again")
            time.sleep(0.001)
        else:
            break
    s.send(bytes(sv.dumps(message), SC.ENCODING_TYPE))
    raw_response_string = recv_timeout(s)
    # raw_response_string = s.recv(SC.MSG_BUFFER_SIZE).decode(SC.ENCODING_TYPE)
    #print("raw_response_string: ", raw_response_string)
    try:
        response = sv.loads(raw_response_string)
    except Exception as e:
        print("Exception while loading serialized response: ", e)
        f = open('raw_response_string.txt', 'w')
        f.write(raw_response_string)
        f.close()
    data_transferred_size += get_size(response)
    print("<---" + destination_str)
    print("\t" + SC.MSG_TITLE + ": " + str(response[SC.MSG_TITLE]))
    #print("\t" + SC.MSG_BODY + ": " + str(response[SC.MSG_BODY]))
    s.close()
    if SC.DEBUG_FLAG:
        print("data_transferred_size", data_transferred_size)
    return response

def parse_request_json(request):
    raw_req_string = recv_timeout(request)
    # raw_req_string = request.recv(SC.MSG_BUFFER_SIZE).decode(SC.ENCODING_TYPE)
    try:
        request_data = sv.loads(raw_req_string) #data loaded
    except Exception as e:
        print("Exception while loading serialized request: ", e)
        f = open('raw_req_string.txt', 'w')
        f.write(raw_req_string)
        f.close()
    global data_transferred_size
    data_transferred_size += get_size(request_data)
    print("<---" + str(request_data[SC.MSG_ORIGIN]))
    print("\t" + SC.MSG_TITLE + ": " + str(request_data[SC.MSG_TITLE]))
    #print("\t" + SC.MSG_BODY + ": " + str(request_data[SC.MSG_BODY]))
    if SC.DEBUG_FLAG:
        print("data_transferred_size", data_transferred_size)
    return request_data

def send_response_json(request, response, destination):
    print("--->" + str(destination))
    print("\t" + SC.MSG_TITLE + ": " + str(response[SC.MSG_TITLE]))
    #print("\t" + SC.MSG_BODY + ": " + str(response[SC.MSG_BODY]))
    global data_transferred_size
    data_transferred_size += get_size(response)
    serialized_response = bytes(sv.dumps(response), SC.ENCODING_TYPE)
    request.sendall(serialized_response)
    if SC.DEBUG_FLAG:
        print("data_transferred_size", data_transferred_size)

def get_size(msg):
    return len(sv.dumps(msg))

def recv_timeout(the_socket,timeout=0.1):
    """ Method used to allow for large data transfers"""
    #make socket non blocking
    the_socket.setblocking(0)
    #total data partwise in an array
    total_data=[];
    data='';
    #beginning time
    begin=time.time()
    while True:
        #if you got some data, then break after timeout
        if total_data and time.time()-begin > timeout:
            break
        #if you got no data at all, wait a little longer, twice the timeout
        #elif time.time()-begin > timeout*2:
        #    break
        #recv something
        try:
            data = the_socket.recv(SC.MSG_BUFFER_SIZE).decode(SC.ENCODING_TYPE)
            if data:
                total_data.append(data)
                #change the beginning time for measurement
                begin=time.time()
            else:
                #sleep for sometime to indicate a gap
                time.sleep(0.0001)
        except:
            pass
    #join all parts to make final string
    return ''.join(total_data)
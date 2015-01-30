'''Mix Server'''
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
import sv_tally
import sv_prover
import sv

" ids for MixServers are based on the position in the broadcasted network list"
class MixServer(GenericServer):
    def __init__(self, server_address, RequestHandlerClass, election_parameters):
        GenericServer.__init__(self, server_address, RequestHandlerClass)
        self.election = sv_election.Election(election_parameters)
        # self.sbb_hash = None
        # self.challenges = None

class MixHandler(GenericHandler):
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
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_SPLIT_VALUE_VOTES:
            response = self.handle_get_split_value_votes(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_MIX:
            response = self.handle_mix(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_TALLY:
            response = self.handle_tally(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_PROVE:
            response = self.handle_prove(request_data)
        elif request_data[SC.MSG_TITLE] == SC.MESSAGE_UPDATE_SDB_DATABASE:
            response = self.handle_update_sdb(request_data)
        else:
            response = self.handle_unexpected_request()
        send_response_json(self.request, response, request_data[SC.MSG_ORIGIN])

    def handle_get_split_value_votes(self, request_data):
        """ Voter -> Mix [Distribute Votes]
        Input: Split Value Votes
        Action: Record split value vote parts
        Output: Done """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        (race_id, i, sdbp) = request_data[SC.MSG_BODY]
        self.server.election.server.sdb[race_id][i][0] = sdbp
        if self.server.role_index == self.server.election.server.get_server_index(i,0):
            self.server.election.server.sdb[race_id][i][0] = sdbp
        response[SC.MSG_BODY] = "Done"
        return response

    def handle_mix(self, request_data):
        """ Controller -> Mix [Mix Votes]
        Input: Request to Mix, phase
        Action: Mix Votes
        Output: Done """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        phase = request_data[SC.MSG_BODY]
        role_index = self.server.role_index
        row_index = self.server.election.server.get_server_row_index(role_index)
        col_index = self.server.election.server.get_server_col_index(role_index)
        num_columns = self.server.election.server.cols
        if phase == 0:
            # self.server.election.server.mix()
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 1:
            if col_index == 0: # only first column has input to be replicated
                self.server.election.server.mix_phase_replicate_input(row_index, col_index)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 2:
            if row_index == 'a': # only first row is enough and info is propagated each column
                dict_update_to_share = self.server.election.server.mix_phase_generate_permutations(row_index, col_index)
                target_servers = [] # propagating updates to serves in the same column
                for target_row in self.server.election.server.row_list:
                    if target_row == row_index:
                        continue
                    target_role_idx = self.server.election.server.get_server_index(target_row, col_index)
                    target_servers.append(self.server.servers_alive[SC.ROLE_MIX][target_role_idx])
                for s in target_servers:
                    response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_UPDATE_SDB_DATABASE, body = dict_update_to_share, origin = (self.server.server_address[0], self.server.server_address[1]), auth = "")
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 3:
            if row_index == 'a': # only first row is enough and info is propagated each column
                dict_update_to_share = self.server.election.server.mix_phase_generate_obfuscation_values(row_index, col_index)
                target_servers = [] # propagating updates to serves in the same column
                for target_row in self.server.election.server.row_list:
                    if target_row == row_index:
                        continue
                    target_role_idx = self.server.election.server.get_server_index(target_row, col_index)
                    target_servers.append(self.server.servers_alive[SC.ROLE_MIX][target_role_idx])
                for s in target_servers:
                    response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_UPDATE_SDB_DATABASE, body = dict_update_to_share, origin = (self.server.server_address[0], self.server.server_address[1]), auth = "")
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase > 3 and phase <= 3+num_columns:
            # get it on (i,j) forward it to (i,j+1), first process all 1st column, when ready, all 2nd column
            if col_index == phase-4 and col_index != num_columns-1: # one column at a time, data is propagated left-to-right
                dict_update_to_share = self.server.election.server.mix_phase_process_left_to_right(row_index, col_index)
                target_role_idx = self.server.election.server.get_server_index(row_index, col_index+1)
                s = self.server.servers_alive[SC.ROLE_MIX][target_role_idx]
                response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_UPDATE_SDB_DATABASE, body = dict_update_to_share, origin = (self.server.server_address[0], self.server.server_address[1]), auth = "")
            elif col_index == phase-4 and col_index == num_columns-1: # one column at a time, data is propagated left-to-right
                dict_update_to_share = self.server.election.server.mix_phase_process_left_to_right(row_index, col_index)
                target_servers = []
                for target_row in self.server.election.server.row_list:
                    if target_row == row_index:
                        continue
                    target_role_idx = self.server.election.server.get_server_index(target_row, col_index)
                    target_servers.append(self.server.servers_alive[SC.ROLE_MIX][target_role_idx])
                for s in target_servers: # TODO this should happen only for k in opl -> move this to tally phase
                    response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_UPDATE_SDB_DATABASE, body = dict_update_to_share, origin = (self.server.server_address[0], self.server.server_address[1]), auth = "")
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        else:
            response[SC.MSG_BODY] = "Done"
        
        # self.server.election.server.test_mix() -> TODO is this the correct test? Ron was not running it
        print("Mixing", response[SC.MSG_BODY])
        return response

    def handle_prove(self, request_data):
        """ Controller -> Mix [Prove]
        Input: Request proofs, phase
        Action: Make Proofs, post to SBB
        Output: Done """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        phase = request_data[SC.MSG_BODY]
        role_index = self.server.role_index
        row_index = self.server.election.server.get_server_row_index(role_index)
        col_index = self.server.election.server.get_server_col_index(role_index)
        cols = self.server.election.server.cols
        election = self.server.election
        # Prove!
        if phase == 0:
            msg_header, msg_dict = sv_prover.compute_output_commitments(election, row_index, col_index)
            if col_index == cols-1:
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=False)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 1:
            # as of now, this phase cannot be done simultaneously by multiple servers, because of modifications on sbb
            sbb_hash_hex = self.server.ask_sbb_hash(public=True)
            sbb_hash = sv.hex2bytes(sbb_hash_hex)
            msg_header, msg_dict = sv_prover.make_cut_verifier_challenges(election, sbb_hash)
            if role_index == cols * self.server.election.server.rows -1: # last server so that other sbb_hash not affected
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=False)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 2:
            dict_update_to_share = sv_prover.share_icl_pik_dict(election, election.server.challenges, row_index, col_index)
            for s in self.server.servers_alive[SC.ROLE_MIX]:
                if s[0] == self.server.server_address[0] and s[1] == self.server.server_address[1]:
                    continue # skips itself
                response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_UPDATE_SDB_DATABASE, body = dict_update_to_share, origin = (self.server.server_address[0], self.server.server_address[1]), auth = "")
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 3:
            msg_header, msg_dict = sv_prover.compute_and_post_pik_dict(election, election.server.challenges, row_index, col_index)
            if role_index == 0:
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=False)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 4:
            if col_index == 0:
                dict_update_to_share = sv_prover.share_icl_ux_uy_dict(election, election.server.challenges, row_index, col_index)
                target_role_idx = self.server.election.server.get_server_index(row_index, cols-1)
                s = self.server.servers_alive[SC.ROLE_MIX][target_role_idx] # sensitive information only share it with server in same row, last column
                response = json_client(ip = s[0], port = s[1], title = SC.MESSAGE_UPDATE_SDB_DATABASE, body = dict_update_to_share, origin = (self.server.server_address[0], self.server.server_address[1]), auth = "")
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 5:
            if col_index == cols-1:
                msg_header, msg_dict = sv_prover.compute_and_post_t_values(election, election.server.challenges, row_index, col_index)
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=False)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 6:
            # as of now, this phase cannot be done simultaneously by multiple servers, because of modifications on sbb
            sbb_hash_hex = self.server.ask_sbb_hash(public=True)
            sbb_hash = sv.hex2bytes(sbb_hash_hex)
            msg_header, msg_dict = sv_prover.make_leftright_verifier_challenges(election, sbb_hash)
            if role_index == cols * self.server.election.server.rows -1: # last server so that other sbb_hash not affected
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=False)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 7:
            if col_index == cols-1:
                msg_header, msg_dict = sv_prover.prove_outcome_correct(election, election.server.challenges, row_index, col_index)
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=False)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 8:
            if col_index == 0:
                msg_header, msg_dict = sv_prover.prove_input_consistent_input_openings(election, election.server.challenges, row_index, col_index)
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=False)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        elif phase == 9:
            if col_index == cols-1:
                msg_header, msg_dict = sv_prover.prove_input_consistent_output_openings(election, election.server.challenges, row_index, col_index)
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=False)
            response[SC.MSG_BODY] = "phase "+ str(phase) + " completed for role_index " + str(role_index)
        else:
            response[SC.MSG_BODY] = "Done"
        print("Proof", response[SC.MSG_BODY])
        return response

    def handle_tally(self, request_data):
        """ Controller -> Mix [Tally Votes]
        Input: Request to Tally
        Action: Tally Votes, Ask SBB to post
        Output: Done """
        role_index = self.server.role_index
        row_index = self.server.election.server.get_server_row_index(role_index)
        col_index = self.server.election.server.get_server_col_index(role_index)
        num_columns = self.server.election.server.cols
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        if col_index == num_columns-1:
            msg_header, msg_dict = sv_tally.compute_tally(self.server.election)
            sv_tally.print_tally(self.server.election)
            if row_index == 'a': # only one server sends tally to SBB
                # Save tallies to sbb.
                self.server.ask_sbb_to_post(msg_header, msg_dict, time_stamp=True)
        response[SC.MSG_BODY] = "Done"
        return response

    def handle_update_sdb(self, request_data):
        """ Mix -> Mix
        Input: dict update
        Action: update sdb
        Output: Done """
        response = self.get_incomplete_response(request_data[SC.MSG_TITLE])
        dict_update = request_data[SC.MSG_BODY]
        self.server.election.server.sdb = sv.update_nested_dict(self.server.election.server.sdb, dict_update)
        response[SC.MSG_BODY] = "Done"
        return response

if __name__ == "__main__":
    response = json_client(ip = SC.CONTROLLER_HOST, port = SC.CONTROLLER_PORT, title = SC.MESSAGE_PING_CONTROLLER_1, body = "" , origin = "", auth = "")
    ip, port = response[SC.MSG_BODY]
    # Create the server, binding to the same ip address
    server, server_addr = getTCPSocketServer(Handler = GenericHandler, addr = (ip, port))
    # Let Controller know to which address server is listening to
    response = json_client(ip = SC.CONTROLLER_HOST, port = SC.CONTROLLER_PORT, title = SC.MESSAGE_PING_CONTROLLER_2, body = SC.ROLE_MIX, origin = server_addr, auth = "")
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server_thread = threading.Thread(target=server.serve_forever, daemon = True)
    #daemon threads allow us to finish the program execution, even though some threads may be running
    server_thread.start()
    stop = input("Stop?")
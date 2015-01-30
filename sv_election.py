# sv_election.py
# python3

""" Defines election class, and can run simulated election.
#   0A. Turn on Instances
#   0B. Start Controller Server
#   1. Start Generic Servers, and have them ping the controller. Wait for enough servers
#   2. Controller Initializes each server
        TODO add public key or digital signature
#   2.1 Posting setup info to SBB
#   3. Controller broadcast Network Info
        TODO broadcast auth keys as well
#   4. Produce Votes
#   5. Distribute Votes
#   6. Mix Votes
#   7. Prove
#   8. Tally
#   9. Stop election and close sbb
#   -1. Verify
"""

# MIT open-source license.
# (See https://github.com/ron-rivest/split-value-voting.git)

import sv
import sv_prover
import sv_server
import sv_race
import sv_sbb
import sv_tally
import sv_voter
import sv_verifier

#import socketserver
import ServerConfiguration as SC##information about network
import threading
#import socket
import sys
from ServerController import ControllerServer
from ServerController import ControllerHandler
from ServerController import data_transferred_size
import ServerController
import time

class Election:
    """ Implements a (simulated) election. """

    def __init__(self, election_parameters):
        """ Initialize election object.

        Initialize election, where election_parameters is a dict
        with at least the following key/values:
            "election_id" is a string
            "ballot_style" is a list of (race_id, choices) pairs,
               in which
                   race_id is a string
                   choices is list consisting of
                       one string for each allowable candidate/choice name, or
                       a string "******************" of stars
                           of the maximum allowable length of a write-in
                           if write-ins are allowed.

                Example:
                  ballot_style = [("President", ("Smith", "Jones", "********"))]
                defines a ballot style with one race (for President), and
                for this race the voter may vote for Smith, for Jones, or
                may cast a write-in vote of length at most 8 characters.
            "n_voters" is the number of simulated voters
            "n_reps" is the parameter for the cut-and-choose step
                     (n_reps replicas are made)
                     (in our paper, n_reps is called "2m")
            "n_fail" is the number of servers that may fail
            "n_leak" is the number of servers that may leak
        """

        self.election_parameters = election_parameters

        # mandatory parameters
        election_id = election_parameters["election_id"]
        ballot_style = election_parameters["ballot_style"]
        n_voters = election_parameters["n_voters"]
        n_reps = election_parameters["n_reps"]
        n_fail = election_parameters["n_fail"]
        n_leak = election_parameters["n_leak"]
        # optional parameters (with defaults)
        ballot_id_len = election_parameters.get("ballot_id_len", 32)
        json_indent = election_parameters.get("json_indent", 0)
        self.json_indent = json_indent
        sv.set_json_indent(json_indent)

        # check and save parameters
        assert isinstance(election_id, str) and len(election_id) > 0
        self.election_id = election_id

        assert isinstance(ballot_style, list) and len(ballot_style) > 0
        self.ballot_style = ballot_style

        assert isinstance(n_voters, int) and n_voters > 0
        self.n_voters = n_voters
        # p-list is list ["p0", "p1", ..., "p(n-1)"]
        # these name the positions in a list of objects, one per voter.
        # they are not voter ids, they are really names of positions
        # used for clarity and greater compatibility with json
        # keep all the same length (use leading zeros) so that
        # json "sort by keys" options works.
        # the following list is in sorted order!
        self.p_list = sv.p_list(n_voters)

        assert isinstance(n_reps, int) and \
            0 < n_reps <= 26 and n_reps % 2 == 0
        self.n_reps = n_reps
        # Each copy will be identified by an upper-case ascii letter
        self.k_list = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:n_reps]

        assert isinstance(n_fail, int) and n_fail >= 0
        assert isinstance(n_leak, int) and n_leak >= 0
        self.n_fail = n_fail
        self.n_leak = n_leak

        assert ballot_id_len > 0
        self.ballot_id_len = ballot_id_len

        self.about_text = \
        ["Secure Bulletin Board for Split-Value Voting Method Demo.",
         "by Michael O. Rabin and Ronald L. Rivest",
         "For paper: see http://people.csail.mit.edu/rivest/pubs.html#RR14a",
         "For code: see https://github.com/ron-rivest/split-value-voting",
        ]
        self.legend_text = \
        ["Indices between 0 and n_voters-1 indicated by p0, p1, ...",
         "Rows of server array indicated by a, b, c, d, ...",
         "Copies (n_reps = 2m passes) indicated by A, B, C, D, ...",
         "'********' in ballot style indicates a write-in option",
         "           (number of stars is max write-in length)",
         "Values represented are represented modulo race_modulus.",
         "'x' (or 'y') equals u+v (mod race_modulus),",
         "             and is a (Shamir-)share of the vote.",
         "'cu' and 'cv' are commitments to u and v, respectively.",
         "'ru' and 'rv' are randomization values for cu and cv.",
         "'icl' stands for 'input comparison list',",
         "'opl' for 'output production list';",
         "      these are the 'cut-and-choose' results",
         "      dividing up the lists into two sub-lists.",
         "'time' is time in ISO 8601 format."
        ]
        self.legend_text = ["TODO:"]
        #TODO fix legend_text I was getting some out of bounds error, most likely due to the encoding
        

        self.races = []
        self.race_ids = [race_id for (race_id, choices) in ballot_style]
        self.setup_races(ballot_style)
        self.voters = []
        self.voter_ids = []
        self.setup_voters(self, self.n_voters)
        self.cast_votes = dict()
        self.initialize_cast_votes()
        self.output_commitments = dict()
        self.server = sv_server.Server(self, n_fail, n_leak)

    def run_election(self):
        """ Run a (simulated) election. """
        time_performance = {}
        pretty_start_time = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        start_time = time.time()
        time_performance["0 Election begins"] = time.time() - start_time
        #   0B. Start Controller Server
        # Create the server, binding to 127.0.0.1
        server = ControllerServer((SC.CONTROLLER_HOST, SC.CONTROLLER_PORT), ControllerHandler) #or use a ThreadedTCPServer to handle each request in a different thread.    
        # Activate the server; this will keep running until you interrupt the program with Ctrl+C
        server_thread = threading.Thread(target=server.serve_forever, daemon = True)
        #daemon threads allow us to finish the program execution, even though some threads may be running
        server_thread.start()
        time_performance["0.B Start Controller Server"] = time.time() - start_time
        
        #   1. Start Generic Servers, and have them ping the controller. Wait for enough servers
        num_servers_per_role = self.get_num_servers()
        # Waiting to get enough servers
        server.wait_for_servers(num_servers_per_role)
        time_performance["1 Ping Controller"] = time.time() - start_time

        #   2. Controller Initializes each server
        # assigning and communicating individually
        initialization_params_per_role = self.get_initialization_params_per_role()
        server.assign_server_roles(num_servers_per_role, initialization_params_per_role)
        server.test_assigned_server_roles()
        self.setup_keys() # TODO actually do key setup
        #   2.1 Posting setup info to SBB
        self.post_setup_info_to_sbb(server)
        time_performance["2 Assign Roles"] = time.time() - start_time

        #   3. Controller broadcast Network Info
        server.broadcast_network()
        time_performance["3 Broadcast all roles"] = time.time() - start_time

        #     4. Produce Votes
        server.ask_to_produce_votes(self.election_id)
        # Before returning Voter asks SBB to post voter receipts
        # (in practice SBB does need to post it, voters would get it 
        # and they could compute hash from commitments in SBB)
        time_performance["4 Produce votes"] = time.time() - start_time
        
        #     5. Distribute Votes
        server.ask_voters_to_distribute_votes()
        # Before returning Voter asks SBB to post voter commitments. 
        # This posting to SBB can be transferred to the 1st column of Mix Servers,
        # to handle other adversarial models
        time_performance["5 Distribute votes"] = time.time() - start_time
        
        #     6. Mix Votes
        server.ask_mixservers_to_mix()
        time_performance["6 Mix"] = time.time() - start_time

        #     7. Prove
        server.ask_mixservers_for_proofs()
        # TODO modify prover so that posts come from each server based on the info they have,
        #  if they don't have info keep {} so that update_nested_dict does not mess it up
        time_performance["7 Prove"] = time.time() - start_time

        #     8. Tally
        server.ask_mixservers_for_tally()
        time_performance["8 Tally"] = time.time() - start_time
        
        #     9. Stop election and close sbb
        server.ask_sbb_to_post("election:done.",
                      {"election_id": self.election_id})
        server.ask_sbb_to_close()
        
        print("election finished.")
        print()
        
        #     -1. Verify
        sbb_filename = self.election_id + ".sbb.txt"
        server.ask_sbb_to_print(public=True, sbb_filename=sbb_filename)
        print("beginning verification...")
        server.ask_sbb_to_verify(sbb_filename)
        print("done. (", self.election_id, ")")
        time_performance["9 Verify SBB"] = time.time() - start_time

        #     -2. Get performance stats and save it to disk
        if SC.DEBUG_FLAG:
          performance_stats = {}
          print("Start time for simulation:", pretty_start_time)
          performance_stats["Start time for simulation:"] = pretty_start_time
          print("Network Information:", sv.dumps(server.servers_alive))
          performance_stats["Network Information:"] = server.servers_alive
          print("time_performance:", sv.dumps(time_performance))
          performance_stats["time_performance"] = time_performance
          print("Election Parameters:", sv.dumps(self.election_parameters))
          performance_stats["Election Parameters:"] = self.election_parameters
          print("Data transferred:", ServerController.data_transferred_size)
          performance_stats["Data transferred by Controller:"] = ServerController.data_transferred_size
          print("Performance stats written to " + self.election_id +".performance_stats.txt")
          sv.dump(performance_stats, self.election_id+".performance_stats.txt")


        # write performance stats to disk
        # include network information and date (to describe test)
        # include data transferred for each server
        # include overall time to run election, time_performance

        stop = input("Stop?")
        server.shutdown()
        sys.exit()

    def get_num_servers(self):
        num_servers_per_role = {}
        num_servers_per_role[SC.ROLE_VOTER] = 1
        num_servers_per_role[SC.ROLE_SBB] = 1
        num_servers_per_role[SC.ROLE_MIX] = sv_server.get_num_servers(self.n_fail, self.n_leak)
        return num_servers_per_role

    def get_initialization_params_per_role(self):
        initialization_params_per_role = {}
        initialization_params_per_role[SC.ROLE_VOTER] = self.election_parameters
        initialization_params_per_role[SC.ROLE_SBB] = self.election_parameters
        initialization_params_per_role[SC.ROLE_MIX] = self.election_parameters
        return initialization_params_per_role

    def post_setup_info_to_sbb(self, server):
        server.ask_sbb_to_post("setup:start",
                      {"about": self.about_text,
                       "election_id": self.election_id,
                       "legend": self.legend_text
                      }
                     )
        server.ask_sbb_to_post("setup:voters",
                      {"n_voters": self.n_voters,
                       'ballot_id_len': self.ballot_id_len},
                      time_stamp=False)
        if False:
            if n_voters <= 3:
                server.ask_sbb_to_post("(setup:voter_ids)",
                              {"list": self.voter_ids})
            else:
                server.ask_sbb_to_post("(setup:voter_ids)",
                              {"list": (self.voter_ids[0],
                                        "...",
                                        self.voter_ids[-1])},
                              time_stamp=False)
        race_dict = dict()
        for (race_id, choices) in self.ballot_style:
            race = sv_race.Race(self, race_id, choices)
            race_dict[race_id] = {"choices": race.choices, "race_modulus": race.race_modulus}
        server.ask_sbb_to_post("setup:races", {"ballot_style_race_dict": race_dict}, time_stamp=False)
        # post on log that server array is set up
        server.ask_sbb_to_post("setup:server-array",
                          {"rows": self.server.rows, "cols": self.server.cols,
                           "n_reps": self.n_reps,
                           "threshold": self.server.threshold,
                           'json_indent': self.json_indent},
                          time_stamp=False)
        server.ask_sbb_to_post("setup:finished")

    def setup_races(self, ballot_style):
        """ Set up races for this election, where ballot_style is
        a list of (race_id, choices) pairs, and where
            race_id is a string
            choices is list consisting of
               one string for each allowable candidate/choice name
               a string "******************" of stars
                  of the maximum allowable length of a write-in
                  if write-ins are allowed.

        Example:
          ballot_style = [("President", ("Smith", "Jones", "********"))]
             defines a ballot style with one race (for President), and
             for this race the voter may vote for Smith, for Jones, or
             may cast a write-in vote of length at most 8 characters.
        """
        # check that race_id's are distinct:
        race_ids = [race_id for (race_id, choices) in ballot_style]
        assert len(race_ids) == len(set(race_ids))

        for (race_id, choices) in ballot_style:
            race = sv_race.Race(self, race_id, choices)
            self.races.append(race)

    def setup_voters(self, election, n_voters):
        """ Set up election to have n_voters voters in this simulation. """

        assert isinstance(n_voters, int) and n_voters > 0

        # voter identifier is merely "voter:" + index: voter:0, voter:1, ...
        for i in range(n_voters):
            vid = "voter:" + str(i)
            self.voter_ids.append(vid)
            px = election.p_list[i]
            voter = sv_voter.Voter(self, vid, px)
            self.voters.append(voter)

    def initialize_cast_votes(self):
        """ Initialize the election data structure to receive the cast votes.

            This data structure is updated by voter.cast_vote in sv_voter.py
        """
        cvs = dict()
        for race_id in self.race_ids:
            cvs[race_id] = dict()
            for px in self.p_list:
                cvs[race_id][px] = dict()    # maps row i to vote share
        self.cast_votes = cvs

    def setup_keys(self):
        """ Set up cryptographic keys for this election simulation.

        Not done here in this simulation for simplicity.
        """
        pass
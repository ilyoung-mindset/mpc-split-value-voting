# sv_main.py
# python3
# Ronald L. Rivest and Michael O. Rabin
# 2014-06-26

"""
Top-level routine for running simulated election using split-value method.

Usage:
        python3 sv_main.py
  or
        python3 sv_main.py election_id
        where election description is given in election_id.parameters.txt
"""

# MIT open-source license.
# (See https://github.com/ron-rivest/split-value-voting.git)

import sys
assert sys.version_info[0] == 3

import sv
import sv_election

default_election_parameters = {
    "election_id": "default_election",
    "ballot_style":\
    [("taxes", ("yes", "no")),
     ("mayor", ("tom",
                "rufus",
                "****************"))],  # 16-char write-ins allowed
    "n_voters": 1000,   # voters # TODO run tests with 100, 1000 and 10000 (?)
    "n_reps": 24,         # (# of replicas aka 2m) # TODO if increase 2m, increase MSG_BUFFER_SIZE
    "n_fail": 0,         # how many servers may fail  #TODO change it back to 1
    "n_leak": 2,         # how many servers may leak

    # optional parameters:
    # number of hex digits in ballot id (default 32)
    "ballot_id_len": 32,
    # number of spaces per tab in json output (>=0, default 0)
    # setting this to 0 reduces readability of SBB output, but
    # also reduces SBB size by roughly 25%
    # Leaving it at None makes output less readable, but even
    # more compact, and the i/o is faster.
    "json_indent": 1
}

def get_election_parameters():
    """ Get election parameters if available, from a file.
        Else use default.
    """
    election_parameters = default_election_parameters
    if len(sys.argv) > 1:
        election_id = sys.argv[1]
        election_parameter_filename = election_id + ".parameters.txt"
        election_parameters = sv.load(election_parameter_filename)
    return election_parameters

def do_election():
    """ Do (simulate) an election. """

    election_parameters = get_election_parameters()
    print("starting election (simulation).")
    print("election parameters:")
    for key in sorted(election_parameters.keys()):
        print("    ", key, "=", election_parameters[key])
    election = sv_election.Election(election_parameters)

    election.run_election()
    print("ELECTION RAN UP TO THE END")

if __name__ == "__main__":
    # import cProfile
    # cProfile.run("do_election()")
    do_election()
split-value-voting-dev
======================

Look at sv_election.py to understand the flow.
To run a simulation, adjust election parameters in sv_main and run the correspding number of instances
for n_fail = 0, n_leak = 1: 1 * sv_main, 1* ServerVoter, 1* ServerSBB, 4* ServerMix. All in a local machine
for n_fail = 1, n_leak = 1: 1 * sv_main, 1* ServerVoter, 1* ServerSBB, 9* ServerMix. All in a local machine

Some TODOs
TODO (optional)-Many of the phases are serialized by the Controller/Coordinator. If it makes sense for performance reasons parts of the code can be parallelized, the main part being when controller communicates with the Mix Servers

TODO-Write test cases  - checking for correct initialization, message transmission,...
TODO-Use internal Bulletin Board as common truth to handle sync and failures
	-Synchronization (phases of mixnet)
-Protect against failure in the middle of execution, drop it.
TODO-Check feasibility of compacting receipt to have a voter check one hash instead of one for each race.
TODO-Symmetric and PK Encryption communication not implemented. keys distributed?
TODO-Choosing a random permutation together. How?
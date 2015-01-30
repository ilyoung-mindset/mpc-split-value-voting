# sv_server.py
# python3
# Ronald L. Rivest
# 2014-06-26

""" Code for server portion of simulated election
    Simulates array of servers for mix
    but not SBB or proof servers.
"""

# MIT open-source license.
# (See https://github.com/ron-rivest/split-value-voting.git)

import sv
from copy import deepcopy


class Server():

    """ Implement server (for proofs and tally).

    An object of this class implements a complete 2D server array;
    for a real implementation these would be implemented
    in a distributed manner with a distinct server for each element
    of the array.
    """

    def __init__(self, election, n_fail, n_leak):
        """ Initialize server.  This is one for the whole election.

        The server array has the given number of rows and columns
        as parts or sub-servers.  Here we simulate the actions of
        these sub-servers.
        n_fail = number of servers that could fail
        n_leak = number of servers that my leak information
        """

        assert isinstance(n_fail, int) and n_fail >= 0
        assert isinstance(n_leak, int) and n_leak >= 0

        self.election = election
        self.n_fail = n_fail
        self.n_leak = n_leak

        if self.n_fail > 0:
            self.cols = 1 + n_leak
            self.rows = 2 + n_fail + n_leak
            self.threshold = 2 + n_leak   # number of rows needed to reconstruct
        else:
            self.cols = 1 + n_leak
            self.rows = 1 + n_leak
            self.threshold = 1 + n_leak
        rows = self.rows
        cols = self.cols
        threshold = self.threshold

        # each row has an identifier in "abcd..."
        assert rows <= 26
        self.row_list = sv.row_list(rows)

        self.challenges = dict()

        # The state of the server in row i, col j is represented
        # here in the dictionary P[race_id][i][j] for the given race
        # where  i in row_list  and 0 <= j < cols.

        # create one top-level dict sdb as database for this main server
        self.sdb = dict()

        # within the top level dict sdb, create a three-dimensional array of
        # sub-dicts for data storage, each addressed as sdb[race_id][i][j]
        for race in election.races:
            race_id = race.race_id
            self.sdb[race_id] = dict()
            for i in self.row_list:
                self.sdb[race_id][i] = dict()
                for j in range(cols):
                    self.sdb[race_id][i][j] = dict()

        # each server has its own random-number source for each race
        # in practice, these could be derived from true random seeds input
        # independently to each server
        for race_id in election.race_ids:
            for i in self.row_list:
                for j in range(cols):
                    rand_name = "server:" + race_id + ":" + \
                                str(i) + ":" + str(j)
                    self.sdb[race_id][i][j]['rand_name'] = rand_name
                    sv.init_randomness_source(rand_name)

        # within each sub-dict sdb[race_id][i][j] create a variety of lists for
        # storage of cast votes and associated data, including 2m-way replicated
        # lists needed for the 2m mixes (passes) needed.
        for race_id in election.race_ids:
            for i in self.row_list:
                # first-column lists for storing cast votes and secrets
                sdbp = self.sdb[race_id][i][0]
                sdbp['ballot_id'] = dict()   # ballot_id (indices from p_list)
                sdbp['cu'] = dict()          # commitments to u
                sdbp['cv'] = dict()          # commitments to v
                sdbp['x'] = dict()           # choice x, where x = u+v mod M
                sdbp['u'] = dict()           # u
                sdbp['v'] = dict()           # v
                sdbp['ru'] = dict()          # randomness to open com(u)
                sdbp['rv'] = dict()          # randomness to open com(v)
                # for all columns, have 2m-way replicated data structures
                for j in range(cols):
                    sdbp = self.sdb[race_id][i][j]
                    for k in election.k_list:
                        sdbp[k] = dict()
                        sdbp[k]['x'] = dict()    # inputs on pass k
                        sdbp[k]['y'] = dict()    # outputs on pass k
                # last-column lists for storing published lists of commitments
                for k in election.k_list:
                    sdbp = self.sdb[race_id][i][self.cols-1][k]
                    sdbp['y'] = dict()
                    sdbp['u'] = dict()
                    sdbp['v'] = dict()
                    sdbp['ru'] = dict()
                    sdbp['rv'] = dict()
                    sdbp['cu'] = dict()
                    sdbp['cv'] = dict()

        # create one top-level dict sdb as database for this main server (a unshared copy of sbd)
        self.sdb = deepcopy(self.sdb) # TODO remove

    def print_sdb(self, filters = []):
        d = self.sdb
        for f in filters:
            d = d[f]
        print("print_sdb filters:"+str(filters)+"\n"+sv.dumps(d))

    def get_server_index(self, row_index, col_index):
        assert row_index in self.row_list
        assert type(col_index)==int
        assert type(self.cols)==int
        return (self.row_list.index(row_index))*self.cols + col_index

    def get_server_row_index(self, role_index):
        assert type(role_index)==int
        return self.row_list[int(role_index/self.cols)]

    def get_server_col_index(self, role_index):
        assert type(role_index)==int
        return role_index % self.cols

    def mix_phase_replicate_input(self, row_index, col_index):
        assert col_index == 0
        election = self.election
        # replicate input to become first-column x inputs for each race & pass
        for race_id in election.race_ids:
            for k in election.k_list:
                i = row_index
                x = self.sdb[race_id][i][0]['x']   # dict of n x's
                self.sdb[race_id][i][0][k]['x'] = x.copy()

    def mix_phase_generate_permutations(self, row_index, col_index):
        assert row_index == 'a'
        election = self.election
        # generate permutations (and inverses) used in each column
        # in practice, these could be generated by row 0 server
        # and sent securely to the others in the same column.
        for race_id in election.race_ids:
            j = col_index
            rand_name = self.sdb[race_id]['a'][j]['rand_name']
            sv.init_randomness_source(rand_name) # optional - TODO remove after transition to unshared memory only
            for k in election.k_list:
                pi = sv.random_permutation(election.p_list, rand_name)
                pi_inv = sv.inverse_permutation(pi)
                for i in self.row_list:
                    self.sdb[race_id][i][j][k]['pi'] = pi
                    self.sdb[race_id][i][j][k]['pi_inv'] = pi_inv
        dict_update_to_share = dict()
        for race_id in election.race_ids:
            dict_update_to_share[race_id] = dict()
            for i in self.row_list:
                dict_update_to_share[race_id][i] = dict()
                j = col_index
                assert type(j)==int
                dict_update_to_share[race_id][i][j] = dict()
                for k in election.k_list:
                    dict_update_to_share[race_id][i][j][k] = dict()
                    dict_update_to_share[race_id][i][j][k]['pi'] = self.sdb[race_id][i][j][k]['pi']
                    dict_update_to_share[race_id][i][j][k]['pi_inv'] = self.sdb[race_id][i][j][k]['pi_inv']
        return dict_update_to_share

    def mix_phase_generate_obfuscation_values(self, row_index, col_index):
        assert row_index == 'a'
        election = self.election
        # generate obfuscation values used in each column
        # in practice, these could be generated by row 0 server
        # and sent securely to the others in the same column.
        for race in election.races:
            race_id = race.race_id
            j = col_index
            rand_name = self.sdb[race_id]['a'][j]['rand_name']
            for k in election.k_list:
                fuzz_dict = dict()      # fuzz_dict[i][pnn]
                for i in self.row_list:
                    fuzz_dict[i] = dict()
                for v in election.p_list:
                    share_list = sv.share(0,
                                          self.rows,
                                          self.threshold,
                                          rand_name,
                                          race.race_modulus)
                    for row, i in enumerate(self.row_list):
                        fuzz_dict[i][v] = share_list[row][1]
                for i in self.row_list:
                    # note that fuzz_dict[i] is dict of size n
                    self.sdb[race_id][i][j][k]['fuzz_dict'] = fuzz_dict[i]
        dict_update_to_share = dict()
        for race_id in election.race_ids:
            dict_update_to_share[race_id] = dict()
            for i in self.row_list:
                dict_update_to_share[race_id][i] = dict()
                j = col_index
                assert type(j)==int
                dict_update_to_share[race_id][i][j] = dict()
                for k in election.k_list:
                    dict_update_to_share[race_id][i][j][k] = dict()
                    dict_update_to_share[race_id][i][j][k]['fuzz_dict'] = self.sdb[race_id][i][j][k]['fuzz_dict']
        return dict_update_to_share

    def mix_phase_process_left_to_right(self, row_index, col_index):
        """This code requires inter-processor communication. """

        election = self.election
        # process columns left-to-right, mixing as you go
        for race in self.election.races:
            race_id = race.race_id
            race_modulus = race.race_modulus
            j = col_index
            for k in election.k_list:
                i = row_index # server has information to mix only for itself
                # shuffle first
                pi = self.sdb[race_id][i][j][k]['pi'] # length n
                # note that pi is independent of i
                x = self.sdb[race_id][i][j][k]['x']   # length n
                xp = sv.apply_permutation(pi, x)      # length n
                # then obfuscate by adding "fuzz"
                fuzz_dict = self.sdb[race_id][i][j][k]['fuzz_dict']
                xpo = dict()
                for v in election.p_list:
                    xpo[v] = (xp[v] + fuzz_dict[v]) % race_modulus
                y = xpo
                self.sdb[race_id][i][j][k]['y'] = y
                # this column's y's become next column's x's.
                # in practice would be sent via secure channels
                if j < self.cols - 1:
                    self.sdb[race_id][i][j+1][k]['x'] = y
        dict_update_to_share = dict()
        for race_id in election.race_ids:
            dict_update_to_share[race_id] = dict()
            i = row_index
            dict_update_to_share[race_id][i] = dict()
            j = col_index
            assert type(j)==int
            dict_update_to_share[race_id][i][j] = dict()
            if j < self.cols - 1:
                dict_update_to_share[race_id][i][j+1] = dict()
            for k in election.k_list:
                dict_update_to_share[race_id][i][j][k] = dict()
                dict_update_to_share[race_id][i][j][k]['y'] = self.sdb[race_id][i][j][k]['y']
                if j < self.cols - 1:
                    dict_update_to_share[race_id][i][j+1][k] = dict()
                    dict_update_to_share[race_id][i][j+1][k]['x'] = self.sdb[race_id][i][j+1][k]['x']
        return dict_update_to_share

    def test_mix(self):
        """ Test that mixing is giving reasonable results. """
        election = self.election
        rows = self.rows
        cols = self.cols
        for race in election.races:
            race_id = race.race_id
            print("Race: ", race_id)
            for k in election.k_list:
                choice_int_list = []
                for v in range(election.n_voters):
                    share_list = \
                        [(i+1, self.sdb[race_id][i][cols-1][k]['y'][v]) \
                         for i in range(rows)]
                    choice_int = sv.lagrange(share_list, election.n_voters, \
                                             self.threshold, race.M)
                    choice_int_list.append(choice_int)
                # print("Copy:", k, choice_int_list)
                choice_str_list = [race.choice_int2str(choice_int) \
                                   for choice_int in choice_int_list]
                print("Copy:", k, choice_str_list)

def get_num_servers(n_fail, n_leak):
    """The server array has the given number of rows and columns
    as parts or sub-servers.  Here we simulate the actions of
    these sub-servers.
    n_fail = number of servers that could fail
    n_leak = number of servers that my leak information
    """
    assert isinstance(n_fail, int) and n_fail >= 0
    assert isinstance(n_leak, int) and n_leak >= 0
    rows = 0
    cols = 0
    threshold = 0
    if n_fail > 0:
        cols = 1 + n_leak
        rows = 2 + n_fail + n_leak
        threshold = 2 + n_leak   # number of rows needed to reconstruct
    else:
        cols = 1 + n_leak
        rows = 1 + n_leak
        threshold = 1 + n_leak
    rows = rows
    cols = cols
    threshold = threshold
    return rows*cols
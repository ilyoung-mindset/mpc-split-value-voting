CONTROLLER_HOST = "127.0.0.1"
CONTROLLER_PORT = 1997

# message composition used for incoming request and outgoing responses
MSG_TITLE = 'title'
MSG_BODY = 'body'
MSG_ORIGIN = 'origin'
MSG_AUTH = 'auth'
MSG_BUFFER_SIZE = 8192 #10000000 #100000000 # 262144# 65536 #8192 TODO fix

# Message Encoding Format
ENCODING_TYPE = 'UTF-8' # other UNICODE, ASCII

# list of server roles
ROLE_GENERIC = "Generic Server"
ROLE_VOTER = "Voter Server"
ROLE_CONTROLLER = "Controller Server"
ROLE_SBB = "SBB Server"
ROLE_MIX = "Mix Server"
ROLES_LIST = [ROLE_GENERIC, ROLE_VOTER, ROLE_CONTROLLER, ROLE_SBB, ROLE_MIX]

# response contains title, body (error), origin, auth, id?
MESSAGE_GET_ROLE = "0 Get Role of Server"
MESSAGE_POST_TO_SBB = "0.1 Post message to SBB"
MESSAGE_PRINT_SBB = "0.2 Print SBB to disk"
MESSAGE_HASH_SBB = "0.3 Compute hash of SBB"
MESSAGE_CLOSE_SBB = "0.4 Close SBB"
MESSAGE_PING_CONTROLLER_1 = "1.a Ping Controller 1"
MESSAGE_PING_CONTROLLER_2 = "1.b Ping Controller 2"
MESSAGE_ASSIGN_ROLE_VOTER = "2.a Assign Role Voter"
MESSAGE_ASSIGN_ROLE_SBB = "2.b Assign Role SBB"
MESSAGE_ASSIGN_ROLE_MIX = "2.c Assign Role Mix"
MESSAGE_BROADCAST_ROLES = "3 Broadcast all roles"
MESSAGE_PRODUCE_VOTES = "4 Produce votes"
MESSAGE_DISTRIBUTE_VOTES = "5.a Distribute votes" # Controller -> Voter
MESSAGE_SPLIT_VALUE_VOTES = "5.b Split Value Votes" # Voter -> Mix Servers
MESSAGE_MIX = "6 Mix" # Controller -> Mix Servers
MESSAGE_UPDATE_SDB_DATABASE = "6.b Updating SDB" # Mix Servers -> Mix Servers
MESSAGE_PROVE = "7 Prove" # Controller -> Mix Servers
MESSAGE_TALLY = "8 Tally" # Controller -> Mix Servers
MESSAGE_VERIFY = "-1 Verify SBB"

DEBUG_FLAG = True
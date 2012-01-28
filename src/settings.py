# -*- coding: utf-8 -*-

# System Settings
DAEMON = False
LOGGING = True
LOG_DIR = ""
LOG_OUT = ["test2"]
LOG_MOD = ["test"]

# Module Settings
# In-Out
# Input-to-Output matrix must be set like following dictionary.
# "Input1", "Output1" is a name of these modules.
# {"Input1":["Output1, Output2..."]
#  "Input2":["Output2, Output3..."]
# ...
# }
# If Outputs list is [] or None, all Output modules are used.
INOUT = {"test":[]}

# Module Configure
# Input
INPUT_SETTINGS = {
                  "test":{"token":1},
                  }

# Output
OUTPUT_SETTINGS = {"test2":{"a":1},
                   }
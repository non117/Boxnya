# -*- coding: utf-8 -*-
import os

# System Settings
DAEMON = False
LOGGING = True
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"log")
LOG_OUT = []
LOG_MOD = []

# Module Settings
ENABLE_MODULES = []
# In-Out
# Input-to-Output matrix must be set like following dictionary.
# "Input1", "Output1" is a name of these modules.
# {"Input1":["Output1, Output2..."]
#  "Input2":["Output2, Output3..."]
# ...
# }
# If Outputs list is [] or None, all Output modules are used.
INOUT = {"twitter":["egosearch"],
         "egosearch":["favbot", "imkayac"],
         "gmail":[]
         }

# Module Configure
# Input
INPUT_SETTINGS = {
                  "gmail":{"username":"", "password":""},
                  "twitter":[{'atokensecret': '', 'atoken': ''},
                             {'atokensecret': '', 'atoken': ''}]
                  }
# Filter
FILTER_SETTINGS = {
                   "egosearch":{
                                "screen_name":["",""],
                                "regexp":"",
                                "enable":[], 
                                "protected":[""] #オプション
                                },
                   }

# Output
OUTPUT_SETTINGS = {
                   "imkayac":{"username":"", "password":"", "sig": ""},
                   "favbot":{"include":["twitter"]}
                   }
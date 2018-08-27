#!/usr/bin/env python3

#   Copyright 2018 Braxton Mckee
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import threading
import argparse
import sys
import time
from object_database import connect
from object_database.service_manager.ServiceManager import ServiceManager

def main(argv):
    parser = argparse.ArgumentParser("Run the main service manager.")

    parser.add_argument("host")
    parser.add_argument("port")

    parsedArgs = parser.parse_args(argv[1:])

    db = connect(parsedArgs.host, parsedArgs.port)

    manager = ServiceManager(db)
    
    manager.run()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

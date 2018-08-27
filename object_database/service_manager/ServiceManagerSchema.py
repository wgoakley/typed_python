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

from object_database import Schema, Indexed, Index, core_schema
from typed_python import *

service_schema = Schema("core.service")

service_schema.DockerImage = NamedTuple(source=str, dockerfile_contents=OneOf(None, str))

@service_schema.define
class Codebase:
    hash = Indexed(str)

    #filename (at root of project import) to contents
    modules = ConstDict(str, str) 

    #the dockerfile we'd like to run in
    image = service_schema.DockerImage

@service_schema.define
class Service:
    name = Indexed(str)
    codebase = OneOf(service_schema.Codebase, None)

    service_module_name = str
    service_class_name = str

    min_ram_gb_required = int
    min_cores_required = int

    #how many do we want?
    target_count = int
    actual_count = int

@service_schema.define
class ServiceInstance:
    service = Indexed(service_schema.Service)
    connection = Indexed(OneOf(None, core_schema.Connection))

    shouldShutdown = bool

    def isNotRunning(self):
        return self.state in ("Stopped", "Failed") or (self.connection and not self.connection.exists())

    def isActive(self):
        """Is this service instance up and intended to be up?"""
        return (
            self.state in ("Running", "Initializing", "Booting") 
                and not self.shouldShutdown 
                and (self.connection is None or self.connection.exists())
            )

    state = Indexed(OneOf("Booting", "Initializing", "Running", "Stopped", "Failed"))
    boot_timestamp = OneOf(None, float)
    start_timestamp = OneOf(None, float)
    end_timestamp = OneOf(None, float)
    failureReason = str


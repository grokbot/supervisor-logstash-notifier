#
# Copyright 2016 Dohop hf.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Test utilities
"""

import json
import os
import subprocess
import threading

from unittest import TestCase
from six.moves import socketserver


class LogstashHandler(socketserver.BaseRequestHandler):
    """
    Save received messages.
    """
    messages = []

    def handle(self):
        self.messages.append(self.request[0].strip().decode())


class BaseSupervisorTestCase(TestCase):
    """
    Base class for running supervisor tests
    """
    maxDiff = None

    def __init__(self, *args, **kwargs):
        super(BaseSupervisorTestCase, self).__init__(*args, **kwargs)
        self.supervisor = None
        self.logstash = None

    def run_supervisor(self, overrides, configuration_file):
        """
        Runs Supervisor
        """
        environment = os.environ.copy()
        environment.update(overrides)

        working_directory = os.path.dirname(__file__)

        configuration = os.path.join(working_directory, configuration_file)
        self.supervisor = subprocess.Popen(
            ['supervisord', '-c', configuration],
            env=environment,
            cwd=os.path.dirname(working_directory),
        )

    def shutdown_supervisor(self):
        """
        Shuts Supervisor down
        """
        self.supervisor.terminate()

    def run_logstash(self):
        """
        Runs a socketserver instance emulating Logstash
        """
        self.logstash = socketserver.UDPServer(
            ('0.0.0.0', 0), LogstashHandler)
        threading.Thread(target=self.logstash.serve_forever).start()
        return self.logstash

    def shutdown_logstash(self):
        """
        Shuts the socketserver instance down
        """
        self.logstash.shutdown()

    def messages(self, clear_buffer=False):
        """
        Returns the contents of the logstash message buffer
        """
        messages = self.logstash.RequestHandlerClass.messages
        parsed_messages = list(map(strip_volatile, messages))
        if clear_buffer:
            self.clear_message_buffer()
        return parsed_messages

    def clear_message_buffer(self):
        """
        Clears the logstash message buffer
        """
        self.logstash.RequestHandlerClass.messages = []


def strip_volatile(message):
    """
    Strip volatile parts (PID, datetime, host) from a logging message.
    """
    volatile = [
        '@timestamp',
        'host',
        'pid',
        'tries',
        'stack_info'
    ]
    message_dict = json.loads(message)
    for key in volatile:
        if key in message_dict:
            message_dict.pop(key)

    return message_dict


def record(eventname, from_state):
    """
    Returns a pre-formatted log line to save on the boilerplate
    """
    return {
        '@version': '1',
        'eventname': eventname,
        'from_state': from_state,
        'groupname': 'messages',
        'level': 'INFO',
        'logger_name': 'supervisor',
        'message': '%s messages' % eventname,
        'path': './logstash_notifier/__init__.py',
        'processname': 'messages',
        'tags': [],
        'type': 'logstash'
    }
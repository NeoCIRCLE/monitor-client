#!/usr/bin/python

from datetime import datetime
import time
import socket
import pika
import psutil
import logging
import os


logging.basicConfig()


class Client:

    env_config = {
        "host": "GRAPHITE_HOST",
        "port": "GRAPHITE_PORT",
        "amqp_user": "GRAPHITE_AMQP_USER",
        "amqp_pass": "GRAPHITE_AMQP_PASSWORD",
        "amqp_queue": "GRAPHITE_AMQP_QUEUE",
        "amqp_vhost": "GRAPHITE_AMQP_VHOST",
    }

    def __init__(self, config):
        """
        Constructor of the client class that is responsible for handling the
        communication between the graphite server and the data source. In
        order to initialize a client you must have the following
        environmental varriables:
        - GRAPHITE_SERVER_ADDRESS:
        - GRAPHITE_SERVER_PORT:
        - GRAPHITE_AMQP_USER:
        - GRAPHITE_AMQP_PASSWORD:
        - GRAPHITE_AMQP_QUEUE:
        - GRAPHITE_AMQP_VHOST:
        Missing only one of these variables will cause the client not to work.
        """
        hostname = socket.gethostname().split('.')
        hostname.reverse()
        separator = '.'
        self.name = 'circle.%(host)s' % {'host': separator.join(hostname)}
        self.server_address = str(os.getenv(self.env_config['host']))
        self.server_port = int(os.getenv(self.env_config['port']))
        self.amqp_user = str(os.getenv(self.env_config['amqp_user']))
        self.amqp_pass = str(os.getenv(self.env_config['amqp_pass']))
        self.amqp_queue = str(os.getenv(self.env_config['amqp_queue']))
        self.amqp_vhost = str(os.getenv(self.env_config['amqp_vhost']))
        host_check = Client.__check_envvar(self.server_address)
        port_check = Client.__check_envvar(self.server_port)
        amqp_pass_check = Client.__check_envvar(self.amqp_pass)
        amqp_user_check = Client.__check_envvar(self.amqp_user)
        amqp_queue_check = Client.__check_envvar(self.amqp_queue)
        amqp_vhost_check = Client.__check_envvar(self.amqp_vhost)
        if host_check:
            print(('%(host)s cannot be found in environmental variables.')
                  % {'host': self.env_config['host']}
                  )
            raise RuntimeError
        if port_check:
            print(('%(port)s cannot be found in environmental variables. ')
                  % {'port': self.env_config['port']}
                  )
            raise RuntimeError
        if amqp_user_check or amqp_pass_check:
            print(('%(user)s or %(pass)s cannot be '
                  'found in environmental variables.')
                  % {'user': self.env_config['amqp_user'],
                     'pass': self.env_config['amqp_pass']}
                  )
            raise RuntimeError
        amqp_pass_check = Client.__check_envvar(self.amqp_pass)
        amqp_user_check = Client.__check_envvar(self.amqp_user)
        if amqp_vhost_check or amqp_queue_check:
            print(('%(queue)s or %(vhost)s cannot be '
                  'found in environmental variables.')
                  % {'queue': self.env_config['amqp_queue'],
                     'vhost': self.env_config['amqp_vhost']}
                  )
            raise RuntimeError
        self.debugMode = config["debugMode"]
        self.kvmCPU = int(config["kvmCpuUsage"])
        self.kvmMem = int(config["kvmMemoryUsage"])
        self.kvmNet = int(config["kvmNetworkUsage"])
        self.beat = 1
        self.valid = True

    @classmethod
    def __check_envvar(cls, variable):
        return variable == "None" or variable == ""

    def connect(self):
        """
        This method creates the connection to the queue of the graphite
        server using the environmental variables given in the constructor.
        Returns true if the connection was successful.
        """
        try:
            credentials = pika.PlainCredentials(self.amqp_user, self.amqp_pass)
            params = pika.ConnectionParameters(host=self.server_address,
                                               port=self.server_port,
                                               virtual_host=self.amqp_vhost,
                                               credentials=credentials)
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            return True
        except RuntimeError:
            print ('[ERROR] Cannot connect to the server. '
                   'Parameters could be wrong.'
                   )
            return False
        except:
            print ('[ERROR] Cannot connect to the server. There is no one '
                   'listening on the other side.'
                   )
            return False

    def disconnect(self):
        """
        Break up the connection to the graphite server. If something went
        wrong while disconnecting it simply cut the connection up.
        """
        try:
            self.channel.close()
            self.connection.close()
        except RuntimeError:
            print('[ERROR] An error has occured '
                  'while disconnecting from the server.'
                  )

    def send(self, message):
        """
        Send the message given in the parameters given in the message
        parameter. This function expects that the graphite server want the
        metric name given in the message body. (This option must be enabled
        on the server. Otherwise it can't parse the data sent.)
        """
        try:
            self.channel.basic_publish(exchange=self.amqp_queue,
                                       routing_key='', body="\n".join(message))
            return True
        except:
            print('[ERROR] An error has occured '
                  'while sending metrics to the server.'
                  )
            return False

    def collect_node(self, metricCollectors):
        """
        It harvests the given metrics in the metricCollectors list. This list
        should be provided by the collectables modul. It is important that
        only the information collected from the node is provided here.
        """
        metrics = []
        for collector in metricCollectors:
            collector_function = collector[0]
            phase = collector[1]
            if (self.beat % phase) is 0:
                stat = collector_function()
                metrics.append(('%(hostname)s.%(name)s %(value)f %(time)d') %
                               {'hostname': self.name,
                                'name': stat.name,
                                'value': stat.value,
                                'time': time.time()})
        return metrics

    def collect_vms(self):
        """
        This method is used for fetching the kvm processes running on the
        node and using the cmdline parameters calculates different types of
        resource usages about the vms.
        """
        metrics = []
        running_vms = []
        procList = psutil.get_process_list()
        beats = {
            'mem': self.beat % self.kvmMem,
            'cpu': self.beat % self.kvmCPU,
            'net': self.beat % self.kvmNet
        }
        for entry in procList:
            try:
                entry_name = entry.name
                if entry_name in "kvm":
                    cmdLine = entry.as_dict()["cmdline"]
                    search = [cmd_param_index for cmd_param_index, cmd_param in
                              enumerate(cmdLine)
                              if cmd_param == "-name"]
                    if not entry.is_running():
                        break
                    memory = [cmd_param_index for cmd_param_index, cmd_param in
                              enumerate(cmdLine)
                              if cmd_param == "-m"]
                    if not entry.is_running():
                        break
                    try:
                        running_vms.append([cmdLine[search[0] + 1],
                                            entry.pid,
                                            int(entry.as_dict()["cmdline"][
                                                memory[0] + 1])])
                    except IndexError:
                        pass
                for vm in running_vms:
                    vm_proc = psutil.Process(vm[1])
                    if ((beats['cpu'] is 0) and vm_proc.is_running()):
                        mem_perc = vm_proc.get_memory_percent() / 100 * vm[2]
                        metrics.append("vm.%s.memory.usage %f %d"
                                       % (vm[0], mem_perc, time.time()))
                    if ((beats['mem'] is 0) and vm_proc.is_running()):
                        systemtime = vm_proc.get_cpu_times().system
                        usertime = vm_proc.get_cpu_times().user
                        sumCpu = systemtime + usertime
                        metrics.append("vm.%s.cpu.usage %f %d"
                                       % (vm[0], sumCpu, time.time()))
                interfaces_list = psutil.network_io_counters(pernic=True)
                if beats['net'] is 0:
                    for vm in running_vms:
                        interfaces_list_enum = enumerate(interfaces_list)
                        for iname_index, iname in interfaces_list_enum:
                            if vm[0] in iname:
                                metrics.append(
                                    ('vm.%(name)s.network.packets_sent_%(interface)s '
                                     '%(data)f %(time)d') %
                                    {'name': vm[0],
                                     'interface': iname,
                                     'time': time.time(),
                                     'data': interfaces_list[iname].packets_sent})
                                metrics.append(
                                    ('vm.%(name)s.network.packets_recv_%(interface)s '
                                     '%(data)f %(time)d') %
                                    {'name': vm[0],
                                     'interface': iname,
                                     'time': time.time(),
                                     'data': interfaces_list[iname].packets_recv})
                                metrics.append(
                                    ('vm.%(name)s.network.bytes_sent_%(interface)s '
                                     '%(data)f %(time)d') %
                                    {'name': vm[0],
                                     'interface': iname,
                                     'time': time.time(),
                                     'data': interfaces_list[iname].bytes_sent})
                                metrics.append(
                                    ('vm.%(name)s.network.bytes_recv_%(interface)s '
                                     '%(data)f %(time)d') %
                                    {'name': vm[0],
                                     'interface': iname,
                                     'time': time.time(),
                                     'data': interfaces_list[iname].bytes_recv})
            except psutil.NoSuchProcess:
                print('[ERROR LOG] Process lost.')
        if (self.beat % 30) is 0:
            metrics.append(
                ('%(host)s.vmcount %(data)d %(time)d') %
                {'host': self.name,
                 'data': len(running_vms),
                 'time': time.time()})
        return metrics

    def get_frequency(self, metricCollectors=[]):
        """
        """
        items = metricCollectors + [["kvmCpuUsage", self.kvmMem], [
            "kvmMemoryUsage", self.kvmCPU], ["kvmNetworkUsage", self.kvmNet]]
        max = items[0][1]
        for item in items:
            if max < item[1]:
                max = item[1]
        return max

    @classmethod
    def print_metrics(cls, metrics):
        for metric in metrics:
            parts = metric.split(' ')
            parts[2] = datetime.fromtimestamp(int(parts[2])).strftime('%Y-%m-%d %H:%M:%S')
            print('********************************************')
            print('[M] %(title)s' % {'title': parts[0]})
            print(' -> data: %(data)s' % {'data': parts[1]})
            print(' -> time: %(time)s' % {'time': parts[2]})

    def run(self, metricCollectors=[]):
        """
        Call this method to start reporting to the server, it needs the
        metricCollectors parameter that should be provided by the collectables
        modul to work properly.
        """
        if self.connect() is False:
            hostdata = self.server_address + ':' + str(self.server_port)
            print("[ERROR] An error has occured while connecting to the "
                  "server on %(host)s."
                  % {'host': hostdata})
            return
        else:
            print('[SUCCESS] Connection established to %(host)s:%(port)s.'
                  % {'host': self.server_address,
                     'port': self.server_port})
        try:
            maxFrequency = self.get_frequency(metricCollectors)
            while True:
                nodeMetrics = self.collect_node(metricCollectors)
                vmMetrics = self.collect_vms()
                metrics = nodeMetrics + vmMetrics
                if self.debugMode == "True":
                    Client.print_metrics(metrics)
                if len(metrics) is not 0:
                    if self.send(metrics) is False:
                        raise RuntimeError
                time.sleep(1)
                self.beat = self.beat + 1
                if ((self.beat % (maxFrequency + 1)) is 0):
                    self.beat = 1
        except KeyboardInterrupt:
            print("[x] Reporting has stopped by the user. Exiting...")
        finally:
            self.disconnect()

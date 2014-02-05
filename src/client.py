#!/usr/bin/python

import time
import socket
import pika
import psutil
import logging
import os


logging.basicConfig()


class Client:

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
        self.name = "circle." + ".".join(hostname)
        if os.getenv("GRAPHITE_SERVER_ADDRESS") is "":
            print("GRAPHITE_SERVER_ADDRESS cannot be found in environmental "
                  "variables"
                  )
            self.valid = False
            return
        if os.getenv("GRAPHITE_SERVER_PORT") is "":
            print("GRAPHITE_SERVER_PORT cannot be found in environmental "
                  "variables. (AMQP standard is: 5672"
                  )
            self.valid = False
            return
        if os.getenv("GRAPHITE_AMQP_USER") is "" or os.getenv(
                "GRAPHITE_AMQP_PASSWORD") is "":
            print("GRAPHITE_AMQP_USER or GRAPHITE_AMQP_PASSWORD cannot be "
                  "found in environmental variables. (AMQP standard is: "
                  "guest-guest)"
                  )
            self.valid = False
            return
        if os.getenv("GRAPHITE_AMQP_QUEUE") is "" or os.getenv(
                "GRAPHITE_AMQP_VHOST") is "":
            print("GRAPHITE_AMQP_QUEUE or GRAPHITE_AMQP_VHOST cannot be "
                  "found in environmental variables."
                  )
            self.valid = False
            return
        self.server_address = str(os.getenv("GRAPHITE_SERVER_ADDRESS"))
        self.server_port = int(os.getenv("GRAPHITE_SERVER_PORT"))
        self.amqp_user = str(os.getenv("GRAPHITE_AMQP_USER"))
        self.amqp_pass = str(os.getenv("GRAPHITE_AMQP_PASSWORD"))
        self.amqp_queue = str(os.getenv("GRAPHITE_AMQP_QUEUE"))
        self.amqp_vhost = str(os.getenv("GRAPHITE_AMQP_VHOST"))
        self.debugMode = config["debugMode"]
        self.kvmCPU = int(config["kvmCpuUsage"])
        self.kvmMem = int(config["kvmMemoryUsage"])
        self.kvmNet = int(config["kvmNetworkUsage"])
        self.beat = 1
        self.valid = True

    def __connect(self):
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
            print ("[ERROR] Cannot connect to the server. "
                   "Parameters could be wrong."
                   )
            return False
        except:
            print ("[ERROR] Cannot connect to the server. There is no one "
                   "listening on the other side."
                   )
            return False

    def __disconnect(self):
        """
        Break up the connection to the graphite server. If something went
        wrong while disconnecting it simply cut the connection up.
        """
        try:
            self.channel.close()
            self.connection.close()
        except RuntimeError:
            print("[ERROR] An error has occured while disconnecting from the "
                  "server."
                  )

    def __send(self, message):
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
            print("[ERROR] An error has occured while sending metrics to the "
                  "server."
                  )
            return False

    def __collectFromNode(self, metricCollectors):
        """
        It harvests the given metrics in the metricCollectors list. This list
        should be provided by the collectables modul. It is important that
        only the information collected from the node is provided here.
        """
        metrics = []
        for collector in metricCollectors:
            if (self.beat % collector[1]) is 0:
                stat = collector[0]()
                metrics.append((self.name + "." +
                                stat.name + " %d" % (stat.value)
                                + " %d" % (time.time())
                                ))
        return metrics

    def __collectFromVMs(self):
        """
        This method is used for fetching the kvm processes running on the
        node and using the cmdline parameters calculates different types of
        resource usages about the vms.
        """
        metrics = []
        running_vms = []
        procList = psutil.get_process_list()
        for entry in procList:
            try:
                entry_name = entry.name
            except psutil._error.NoSuchProcess:
                entry_name = ""
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
        if ((self.beat % 30) is 0):
            metrics.append((self.name + "." + "vmcount" +
                            " %d" % len(running_vms)
                            + " %d" % (time.time())
                            ))
        for vm in running_vms:
            vm_proc = psutil.Process(vm[1])
            if ((self.beat % self.kvmCPU) is 0) and vm_proc.is_running():
                metrics.append(("vm." +
                                vm[0] + "." + "memory.usage" +
                                " %d" % (
                                    vm_proc.get_memory_percent() / 100 * vm[2])
                                + " %d" % (time.time())
                                ))
            if ((self.beat % self.kvmMem) is 0) and vm_proc.is_running():
                metrics.append(("vm." +
                                vm[0] + "." + "cpu.usage" +
                                " %d" % (vm_proc.get_cpu_times().system +
                                         vm_proc.get_cpu_times().user)
                                + " %d" % (time.time())
                                ))
        interfaces_list = psutil.network_io_counters(
            pernic=True)
        interfaces_list_enum = enumerate(interfaces_list)
        if ((self.beat % self.kvmNet) is 0) and vm_proc.is_running():
            for vm in running_vms:
                for iname_index, iname in interfaces_list_enum:
                    if vm[0] in iname:
                        metrics.append(("vm." +
                                        vm[0] +
                                        "." + "network.packages_sent" +
                                        " %d" % interfaces_list[
                                            iname].packets_sent
                                        + " %d" % (time.time())
                                        ))
                        metrics.append(("vm." +
                                        vm[0] +
                                        "." + "network.packages_recv" +
                                        " %d" % interfaces_list[
                                            iname].packets_recv
                                        + " %d" % (time.time())
                                        ))
                        metrics.append(("vm." +
                                        vm[0] + "." + "network"
                                        ".bytes_sent" +
                                        " %d" % interfaces_list[
                                                iname].bytes_sent
                                        + " %d" % (time.time())
                                        ))
                        metrics.append(("vm." +
                                        vm[0] +
                                        + "network.bytes_recv" +
                                        " %d" %
                                        (interfaces_list[iname].bytes_recv)
                                        + " %d" % (time.time())
                                        ))
        return metrics

    def getMaxFrequency(self, metricCollectors=[]):
        """
        """
        items = metricCollectors + [["kvmCpuUsage", self.kvmMem], [
            "kvmMemoryUsage", self.kvmCPU], ["kvmNetworkUsage", self.kvmNet]]
        max = items[0][1]
        for item in items:
            if max < item[1]:
                max = item[1]
        return max

    def startReporting(self, metricCollectors=[]):
        """
        Call this method to start reporting to the server, it needs the
        metricCollectors parameter that should be provided by the collectables
        modul to work properly.
        """
        if self.valid is False:
            print("[ERROR] The client cannot be started.")
            raise RuntimeError
        if self.__connect() is False:
            print("[ERROR] An error has occured while connecting to the "
                  "server on %s."
                  % (self.server_address + ":" + str(self.server_port)))
        else:
            print("[SUCCESS] Connection established to %s on port %s. \
                  Clientname: %s"
                  % (self.server_address, self.server_port,
                     self.name))
        try:
            maxFrequency = self.getMaxFrequency(metricCollectors)
            while True:
                nodeMetrics = self.__collectFromNode(metricCollectors)
                vmMetrics = self.__collectFromVMs()
                metrics = nodeMetrics + vmMetrics
                if self.debugMode == "True":
                    print(metrics)
                if len(metrics) is not 0:
                    if self.__send(metrics) is False:
                        raise RuntimeError
                time.sleep(1)
                self.beat = self.beat + 1
                if ((self.beat % (maxFrequency + 1)) is 0):
                    self.beat = 1
        except KeyboardInterrupt:
            print("[x] Reporting has stopped by the user. Exiting...")
        finally:
            self.__disconnect()

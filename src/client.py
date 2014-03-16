#!/usr/bin/python

from datetime import datetime
from socket import gethostname
import argparse
import logging
import operator
import os
import pika
import psutil
import time

logger = logging.getLogger(__name__)


class Client:

    env_config = {
        "server_address": "GRAPHITE_HOST",
        "server_port": "GRAPHITE_PORT",
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
        self.name = 'circle.%s' % gethostname()
        for var, env_var in self.env_config.items():
            value = os.getenv(env_var, "")
            if value:
                setattr(self, var, value)
            else:
                raise RuntimeError('%s environment variable missing' % env_var)
        self.debugMode = config["debugMode"]
        self.kvmCPU = int(config["kvmCpuUsage"])
        self.kvmMem = int(config["kvmMemoryUsage"])
        self.kvmNet = int(config["kvmNetworkUsage"])
        self.beat = 0

    def connect(self):
        """
        This method creates the connection to the queue of the graphite
        server using the environmental variables given in the constructor.
        Returns true if the connection was successful.
        """
        try:
            credentials = pika.PlainCredentials(self.amqp_user, self.amqp_pass)
            params = pika.ConnectionParameters(host=self.server_address,
                                               port=int(self.server_port),
                                               virtual_host=self.amqp_vhost,
                                               credentials=credentials)
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            logger.info('Connection established to %s.', self.server_address)
        except RuntimeError:
            logger.error('Cannot connect to the server. '
                         'Parameters may be wrong.')
            logger.error("An error has occured while connecting to the server")
            raise
        except:  # FIXME
            logger.error('Cannot connect to the server. There is no one '
                         'listening on the other side.')
            raise

    def disconnect(self):
        """
        Break up the connection to the graphite server. If something went
        wrong while disconnecting it simply cut the connection up.
        """
        try:
            self.channel.close()
            self.connection.close()
        except RuntimeError as e:
            logger.error('An error has occured while disconnecting. %s', unicode(e))
            raise

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
            logger.error('An error has occured while sending metrics.')
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
            if self.beat % phase == 0:
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
        now = time.time()
        running_vms = []
        beats = {
            'mem': self.beat % self.kvmMem == 0,
            'cpu': self.beat % self.kvmCPU == 0,
            'net': self.beat % self.kvmNet == 0
        }

        if beats['cpu'] or beats['mem']:
            for entry in psutil.get_process_list():
                try:
                    if entry.name == 'kvm':
                        parser = argparse.ArgumentParser()
                        parser.add_argument('-name')
                        parser.add_argument('--memory-size', '-m ', type=int)
                        args, unknown = parser.parse_known_args(entry.cmdline[1:])

                        process = psutil.Process(entry.pid)

                        mem_perc = process.get_memory_percent() / 100 * args.memory_size
                        metrics.append('vm.%(name)s.memory.usage %(value)f '
                                       '%(time)d' % {'name': args.name,
                                                     'value': mem_perc,
                                                     'time': now})
                        user_time, system_time = process.get_cpu_times()
                        sum_time = system_time + user_time
                        metrics.append('vm.%(name)s.cpu.usage %(value)f '
                                       '%(time)d' % {'name': args.name,
                                                     'value': sum_time,
                                                     'time': now})
                        running_vms.append(args.name)
                except psutil.NoSuchProcess:
                    logger.warning('Process %d lost.', entry.pid)

        interfaces_list = psutil.network_io_counters(pernic=True)
        if beats['net']:
            for interface, data in interfaces_list.iteritems():
                try:
                    vm, vlan = interface.rsplit('-', 1)
                except ValueError:
                    continue
                if vm in running_vms:
                    for metric in ('packets_sent', 'packets_recv',
                                   'bytes_sent', 'bytes_recv'):
                        metrics.append(
                            'vm.%(name)s.network.%(metric)s-'
                            '%(interface)s %(data)f %(time)d' %
                            {'name': vm,
                             'interface': vlan,
                             'metric': metric,
                             'time': now,
                             'data': getattr(data, metric)})

        if (self.beat % 30) == 0:
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
        freqs = set([i[1] for i in items if i[1]>0])
        return reduce(operator.mul, freqs, 1)

    def run(self, metricCollectors=[]):
        """
        Call this method to start reporting to the server, it needs the
        metricCollectors parameter that should be provided by the collectables
        modul to work properly.
        """
        self.connect()
        try:
            maxFrequency = self.get_frequency(metricCollectors)
            while True:
                nodeMetrics = self.collect_node(metricCollectors)
                vmMetrics = self.collect_vms()
                metrics = nodeMetrics + vmMetrics
                if metrics:
                    if self.debugMode == "True":
                        for i in metrics:
                            logger.debug('Metric to send: %s', i)
                    logger.info("%d metrics sent", len(metrics))
                    if not self.send(metrics):
                        raise RuntimeError
                time.sleep(1)
                self.beat += 1
                if self.beat % maxFrequency == 0:
                    self.beat = 0
        except KeyboardInterrupt:
            logger.info("Reporting has stopped by the user. Exiting...")
        finally:
            self.disconnect()

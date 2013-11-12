#!/usr/bin/python

# import platform
# import collections
import time
import socket
import pika
# import struct
import logging
import os


logging.basicConfig()


class Client:

    def __init__(self, config):
        """
        Constructor of the client requires a configuration provided by cnfparse
        modul. It is a dictionary: {debugMode}
        """
        hostname = socket.gethostname().split('.')
        hostname.reverse()
        self.name = "circle." + ".".join(hostname)
        self.server_address = str(os.getenv("GRAPHITE_SERVER_ADDRESS"))
        self.server_port = int(os.getenv("GRAPHITE_SERVER_PORT"))
        self.debugMode = config["debugMode"]
        self.amqp_user = str(os.getenv("GRAPHITE_AMQP_USER"))
        self.amqp_pass = str(os.getenv("GRAPHITE_AMQP_PASSWORD"))
        self.amqp_queue = str(os.getenv("GRAPHITE_AMQP_QUEUE"))
        self.amqp_vhost = str(os.getenv("GRAPHITE_AMQP_VHOST"))
        self.beat = 1

    def __connect(self):
        """
        This method creates the connection to the queue of the graphite server.
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
        except:
            raise

    def __disconnect(self):
        """
        Break up the connection to the graphite server.
        """
        self.channel.close()
        self.connection.close()

    def __send(self, message):
        """
        Send the message given in the parameters.
        """
        self.channel.basic_publish(exchange=self. amqp_queue,
                                   routing_key='', body="\n".join(message))

    def __collectFromNode(self, metricCollectors):
        """
        It harvests the given metrics in the metricCollectors list. This list
        should be provided by the collectables modul.
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

    def getMaxFrequency(self, metricCollectors=[]):
        max = metricCollectors[0][1]
        for item in metricCollectors:
            if max < item[1]:
                max = item[1]
        return max

    def startReporting(self, metricCollectors=[], debugMode=False):
        """
        Call this method to start reporting to the server, it needs the
        metricCollectors parameter that should be provided by the collectables
        modul to work properly.
        """
        if self.__connect() is False:
            print("An error has occured while connecting to the server on %s"
                  % (self.server_address + ":" + str(self.server_port)))
        else:
            print("Connection established to %s on port %s. \
                  Report frequency is %d sec. Clientname: %s"
                  % (self.server_address, self.server_port,
                     self.delay, self.name))
        try:
            maxFrequency = self.getMaxFrequency(metricCollectors)
            while True:
                metrics = self.__collectFromNode(metricCollectors)
                if self.debugMode == "True":
                    print(metrics)
                self.__send(metrics)
                time.sleep(1)
                self.beat = self.beat + 1
                if ((self.beat % (maxFrequency + 1)) is 0):
                    self.beat = 1
        except KeyboardInterrupt:
            print("Reporting has stopped by the user. Exiting...")
        finally:
            self.__disconnect()

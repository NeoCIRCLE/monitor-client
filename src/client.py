#!/usr/bin/python

import platform, collections, time, socket, pika, struct
import logging
logging.basicConfig()

class Client:

    def __init__(self, config):
        """
        Constructor of the client requires a configuration provided by cnfparse
        modul. It is a dictionary: {server_address, server_port, frequency,
        debugMode, amqp_user, amqp_pass, amqp_queue}.
        """
        hostname = socket.gethostname().split('.')
        hostname.reverse()
        self.name = "circle." + ".".join(hostname)
        self.server_address = str(config["server_address"])
        self.server_port = int(config["server_port"])
        self.delay = int(config["frequency"])
        self.debugMode = config["debugMode"]
        self.amqp_user = str(config["amqp_user"])
        self.amqp_pass = str(config["amqp_pass"])
        self.amqp_queue = str(config["amqp_queue"])
        self.amqp_virtual_host = str(config["amqp_virtual_host"])

    def __connect(self):
        """
        This method creates the connection to the queue of the graphite server.
        Returns true if the connection was successful.
        """
        try:
            credentials = pika.PlainCredentials(self.amqp_user, self.amqp_pass)
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                                host=self.server_address,
                                port=self.server_port,
                                virtual_host=self.amqp_virtual_host,
                                credentials=credentials
                            )
                     )
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
        self.channel.basic_publish(exchange=self.amqp_queue, routing_key='',
            body="\n".join(message))

    def __collectFromNode(self, metricCollectors):
        """
        It harvests the given metrics in the metricCollectors list. This list
        should be provided by the collectables modul.
        """
        metrics = []
        for collector in metricCollectors:
            stat = collector()
            metrics.append((
                self.name + "." + stat.name  +
                " %d" % (stat.value)         +
                " %d" % (time.time())
            ))
        return metrics

    def startReporting(self, metricCollectors = [], debugMode = False):
        """
        Call this method to start reporting to the server, it needs the
        metricCollectors parameter that should be provided by the collectables
        modul to work properly.
        """
        if self.__connect() == False:
            print ("An error has occured while connecting to the server on %s" %
                    (self.server_address + ":" + str(self.server_port)))
        else:
            print("Connection established to %s on port %s. \
                   Report frequency is %d sec. Clientname: %s" %
                  (self.server_address, self.server_port, self.delay, self.name)
                  )
        try:
            while True:
                metrics =  self.__collectFromNode(metricCollectors)
                if self.debugMode == "True":
                    print(metrics)
                self.__send(metrics)
                time.sleep(self.delay)
        except KeyboardInterrupt:
            print("Reporting has stopped by the user. Exiting...")
        finally:
            self.__disconnect()

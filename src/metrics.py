#!/usr/bin/python

import psutil as ps
import collections

####################################################################################
Metrics = collections.namedtuple("Metrics", ["name", "value"])

class Collection (object):

    class Group (object):

       class Metric (object):

            @staticmethod
            def harvest():
                raise NotImplementedError("You must implement the harvest method.")
####################################################################################


class std (Collection):

    class cpu (Collection.Group):

        class usage (Collection.Group.Metric):

            @staticmethod
            def harvest():
                return Metrics("cpu.usage", ps.cpu_percent(0))

    class memory (Collection.Group):

        class usage(Collection.Group.Metric):

            @staticmethod
            def harvest():
                return Metrics("memory.usage", ps.virtual_memory().percent)


    class user (Collection.Group):

        class count (Collection.Group.Metric):

            @staticmethod
            def harvest():
                return Metrics("user.count", len(ps.get_users()))

    class network (Collection.Group):

        class packages_sent (Collection.Group.Metric):

            @staticmethod
            def harvest():
                return Metrics("network.packages_sent",  ps.net_io_counters().packets_sent)

        class packages_received (Collection.Group.Metric):

            @staticmethod
            def harvest():
                return Metrics("network.packages_received",  ps.net_io_counters().packets_recv)

        class bytes_sent (Collection.Group.Metric):

            @staticmethod
            def harvest():
                return Metrics("network.bytes_sent", ps.net_io_counters().bytes_sent)

        class bytes_received(Collection.Group.Metric):

            @staticmethod
            def harvest():
                return Metrics("network.bytes_recv",  ps.net_io_counters().bytes_recv)

    class system (Collection.Group):

        class boot_time (Collection.Group.Metric):

            @staticmethod
            def harvest():
                return Metrics("system.boot_time", ps.get_boot_time())

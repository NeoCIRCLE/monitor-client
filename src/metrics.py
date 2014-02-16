#!/usr/bin/python

import psutil as ps
import collections


#############################################################################
Metrics = collections.namedtuple("Metrics", ["name", "value"])


class Collection(object):

    class Group(object):

        class Metric(object):
            name = "unknown"
            collector_function = 0
            collector_function_arguments = {}
            collector_function_result_attr = ""

            @classmethod
            def harvest(cls):
                query = cls.collector_function.im_func(
                    **cls.collector_function_arguments)
                if ((isinstance(query, list)) or (isinstance(query, dict))):
                    return Metrics(cls.name,
                                   query[cls.collector_function_result_attr])
                elif (isinstance(query, tuple)):
                    return Metrics(cls.name, query.__getattribute__(
                        cls.collector_function_result_attr))
                else:
                    return Metrics(cls.name, query)

##############################################################################


class std(Collection):

    class cpu(Collection.Group):

        class usage(Collection.Group.Metric):
            name = "cpu.usage"
            collector_function = ps.cpu_percent
            collector_function_arguments = {'interval': 0.0}

    class memory(Collection.Group):
        class usage(Collection.Group.Metric):
            name = "memory.usage"
            collector_function = ps.virtual_memory
            collector_function_result_attr = "percent"

    class swap(Collection.Group):
        class usage(Collection.Group.Metric):
            name = "swap.usage"
            collector_function = ps.swap_memory
            collector_function_result_attr = "percent"

    class user(Collection.Group):
        class count(Collection.Group.Metric):
            name = "user.count"

            @classmethod
            def harvest(cls):
                return Metrics(cls.name, len(ps.get_users()))

    class network(Collection.Group):
        class packages_sent(Collection.Group.Metric):
            name = "network.packages_sent"
            collector_function = ps.network_io_counters
            collector_function_result_attr = "packets_sent"

        class packages_received(Collection.Group.Metric):
            name = "network.packages_received"
            collector_function = ps.network_io_counters
            collector_function_result_attr = "packets_recv"

        class bytes_sent(Collection.Group.Metric):
            name = "network.bytes_sent"
            collector_function = ps.network_io_counters
            collector_function_result_attr = "bytes_sent"

        class bytes_received(Collection.Group.Metric):
            name = "network.bytes_received"
            collector_function = ps.network_io_counters
            collector_function_result_attr = "bytes_recv"

    class system(Collection.Group):
        class boot_time(Collection.Group.Metric):
            name = "system.boot_time"
            collector_function = ps.get_boot_time

import configparser

def importConf(path_to_file):
    config = configparser.RawConfigParser(allow_no_value = False)
    try:
        config.read(path_to_file)
        params = {}
        params["frequency"]       =  config.get("Client" , "Frequency")
        params["debugMode"]       =  config.get("Client" , "Debug")
        params["server_address"]  =  config.get("Server" , "Address")
        params["server_port"]     =  config.get("Server" , "Port")
        params["aqmp_queue"]      =  config.get("AMQP"   , "Queue")
        params["aqmp_user"]       =  config.get("AMQP"   , "User")
        params["aqmp_pass"]       =  config.get("AMQP"   , "Pass")
        params["cpu.usage"]       =  config.get("Metrics", "cpuUsage")
        params["memory.usage"]    =  config.get("Metrics", "memoryUsage")
        params["user.count"]      =  config.get("Metrics", "userCount")
        params["swap.usage"]      =  config.get("Metrics", "swapUsage")
        params["system.boot_time"]=  config.get("Metrics", "systemBootTime")
        params["package.traffic"] =  config.get("Metrics", "packageTraffic")
        params["data.traffic"]    =  config.get("Metrics", "dataTraffic")
    except configparser.NoSectionError:
        print("Config file contains error! Reason: Missing section.")
        raise
    except configparser.ParsingError:
        print("Config file contains error! Reason: Cannot parse.")
        raise
    except configparser.MissingSectionHeader:
        print("Config file contains error! Reason: Missing section-header.")
        raise

    return params



import ConfigParser as configparser

def importConf(path_to_file):
    config = configparser.RawConfigParser(allow_no_value = False)
    try:
        config.read(path_to_file)
        params = {}
        metrics = {}
        params["debugMode"]       =  config.get("Client" , "Debug")
        metrics["cpu.usage"]       =  config.get("Metrics", "cpuUsage")
        metrics["memory.usage"]    =  config.get("Metrics", "memoryUsage")
        metrics["user.count"]      =  config.get("Metrics", "userCount")
        metrics["swap.usage"]      =  config.get("Metrics", "swapUsage")
        metrics["system.boot_time"]=  config.get("Metrics", "systemBootTime")
        metrics["network"]    =  config.get("Metrics", "dataTraffic")
    except configparser.NoSectionError:
        print("Config file contains error! Reason: Missing section.")
        raise
    except configparser.ParsingError:
        print("Config file contains error! Reason: Cannot parse.")
        raise
    except configparser.MissingSectionHeader:
        print("Config file contains error! Reason: Missing section-header.")
        raise

    return params, metrics



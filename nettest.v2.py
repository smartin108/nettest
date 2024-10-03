"""

nettest.v2.1

A program that checks connectivity to a list of devices, and attempts to send a text message if a connection fails.

The original intent of this program was to check the connection to the porch desktop because it is error-prone. 
When my desktop on the porch went on the fritz (about one a month), Rebecca's PC would be unable to use the network.
So I wanted a way to know something was going wrong and proactively fix it.

v2 is mostly a rewrite of the original.

Feature comparison:
    *   Status data now tracks when notifications were actually sent, so we can properly implement the wait 
        time between notifications
    *   Status data implemented in json; makes working with a dict structure easy and much less clunky compared to
        the old flat file format
    *   Time data all stored in UTC to avoid any DST disruption
        *   Although I think this is an improvement, I also think I need to do some work to show conversions to local 
            time where it would be easier to contextualize.
    *   Improved logging of events

Change log:

2022 04 30: New code
2022 05 01: WAN IP and gateway are now obtained dynamically using module IPData
2022 05 03: WAN IP and gateway are persisted and updated when they are stale

Bug log / feature requests:

2022-05-03: It appears calling the service providing WAN IP / gateway has some kind of meter/throttle, as there a a few 
    log entries where the service returned '429 Too Many Requests'. It might be a good idea to check this just once per
    day or something, as opposed to every hour when this runs.
    Idea: store the WAN IP & gateway in a JSON file and record the timestamp. Check the timestamp to determine how fresh
    the data is and only call the service when needed.
    Implemented 2022-05-03

2022-07-03: During various outages, no email/text notification can be sent. As a net watcher, I want to be notified when 
    a pernicious outage is resolved. Suggest persisting such outages in the status file along with enough information to
    provide context so that a notification can be sent when the outage is resolved.

2022 07 28: For servers enumerated in nettest.servers.txt, it would be good to know the role they play, in order to enable 
    smarter status messaging. Well, actually it's only the DNS that is subject to change. IDK. 

2023 10 21: v2.1: Add blacklist of known bad server addresses. Rudimentary check WAN addresses for validity and do not 
    ping / update asap if they are invalid.



2024 04 22

HELLO We are managing the codebase somewhat now. 

Here are things you should do or at least prioritize:

*   Tests on any address determined programatically cannot be enabled or 
    disabled in data--this has to be done in code. That needs to change.
    For example, I need to disable *PINGING the WANIP (and presumably the
    gateway). However, I do not wish to stop *KNOWING what the WANIP is. 

*   As an end-user, I need to be able to set preferences for how I receive
    messages. In particular, I may want to know about certain things quickly
    or frequently, others, neither, or never. 





"""


import json
import datetime
from pythonping import ping
import logger
import messenger
import IPData

logname = 'nettest.v2'
filename = f'{logname}.log'
LogInterface = logger.Interface(logname=logname, filename=filename, level='INFO')
log = LogInterface.start()

hours_to_wait_between_failure_notifications = 24
blacklist = ['0.0.0.0', '0.0.0.1']


def write_status(dict_status):
    """Write results of server pings to storage"""
    with open('nettest.status.json', 'w') as f:
        f.write(json.dumps(dict_status))


def write_WANIP_data(dict_wanip):
    """Write discovered WAN IP and gateway IP addresses to storage"""
    with open('nettest.wanip.json', 'w') as f:
        f.write(json.dumps(dict_wanip))


"""

First observation : the two functions above do virtually the same thing.
Even the data files are similar (if inconsistently labeled)

These should be combined into a single write function that specifies which
dictionary should be updated. Likewise, the data files should be consolidated.

"""

def read_status():
    """Read results of previous server pings from storage"""
    try:
        with open('nettest.status.json', 'r') as f:
            try:
                dict_status = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                # the status file is not valid json; we make a new one
                log.info('The status file cannot be parsed as json and will be created anew.')
                return {}
    except FileNotFoundError:
        # the file doesn't exist; we make a new one
        log.info('The status file was not found and will be created.')
        return {}
    return dict_status


def read_WANIP_data():
    """Read WAN IP and gateway IP addresses from storage"""
    try:
        with open('nettest.wanip.json', 'r') as f:
            try:
                dict_wanip = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                # the WAN IP file is not valid json; we make a new one
                log.info('The WAN IP file cannot be parsed as json and will be created anew.')
                return {}
    except FileNotFoundError:
        # the WAN IP file doesn't exist; we make a new one
        log.info('The WAN IP file was not found and will be created.')
        return {}
    return dict_wanip



"""

Second observation : Same as the First (seriously)
Also, these are too complicated. Break up the functionality.

"""



def get_WANIP():
    """Check the WAN IP / gateway IP storage for last known addresses and update them if they are stale"""
    prior_servers = {}
    dict_wanip = read_WANIP_data()
    fresh = False
    if dict_wanip:
        obtained = datetime.datetime.fromisoformat(dict_wanip.get('obtained'))
        age = (datetime.datetime.utcnow() - obtained).total_seconds() / 3600
        # we're only checking the wan ip once a day because the service might complain if we use it too often
        # we know it failed a few times with "too many requests" when checking every 15 minutes


        """
            `age` should be in the persistant storage
        """
        if age < 23.96666667:  # 23 hours 58 minutes, to prevent a recheck from drifting ever later
            fresh = True
        prior_servers = dict_wanip.get('servers')
        if prior_servers.get('wan') in blacklist or prior_servers.get('gateway') in blacklist:
            fresh = False
    if not fresh:
        server = {}
        log.info('The WAN IP data is stale and will be refreshed.')
        MyIP = IPData.IPData()
        server['wan'] = MyIP.get_wan_ip()
        server['gateway'] = MyIP.get_gateway_ip()
        dict_wanip = {'obtained_local_time': datetime.datetime.now().isoformat(), 'obtained': datetime.datetime.utcnow().isoformat(), 'servers': server}
        write_WANIP_data(dict_wanip)
        if prior_servers:
            # this is untested
            # we're trying to detect if the wanip or gateway has changed
            if prior_servers.get('wan') != server.get('wan'):
                # the wan ip has changed?
                send_notification(server.get('wan'), 'The WAN IP has changed since the last time we checked.')
            if prior_servers.get('gateway') != server.get('gateway'):
                # the gateway ip has changed?
                send_notification(server.get('gateway'), 'The gateway IP has changed since the last time we checked.')
        else:
            # we don't actually know the prior servers, which means the file that stores them was missing or borked
            send_notification(server.get('wan'), 'The last known WAP IP cannot be determined. This is the current WAN IP.')

    return dict_wanip.get('servers')


def get_server_list():
    """Read the list of local servers to ping"""
    """ list of servers to be tested is in the file referenced here """
    servers = []
    with open('nettest.servers.txt', 'r') as f:
        line = f.readline()
        while line:
            if line[0] != '#' and line != '':
                servers.append(line.strip('\n'))
            line = f.readline()

    # append WAN IP & gateway dynamically
    # MyIP = IPData.IPData()
    # servers.append(MyIP.get_wan_ip())
    # servers.append(MyIP.get_gateway_ip())
    dynamic_servers = get_WANIP()
    servers.append(dynamic_servers.get('wan'))
    servers.append(dynamic_servers.get('gateway'))
    return servers


def do_ping(server):
    """ ping the server and return the success result (and explanatory message, if failed) 
        This is kludgy per notes below 
        Returns:
            in_alert, alert_description
    """
    try:
        if server not in blacklist:
            response = ping(server)
            if response.success():
                return False, None
            else:
                return True, str(response._responses[-1])
                # not great, I know, but I can't see how else to get at this response text
        else:
            return True, 'The server address is invalid'
    except RuntimeError as e:
        return True, 'unreachable host'
    except Exception as e:
        # (see bugs) -- there is some other kind of exception I need to trap, but I'm not sure what kind it is
        return True, f'Exception: {e}'


def send_notification(server, message):
    """ send a notification. shows how to send a text message via email """
    message_time = f'{datetime.datetime.strftime(datetime.datetime.now(),"%Y-%m-%d %H:%M")}'
    try:
        messenger.Quickmail(
                subject='nettest v2 automated message',
                to='5175124876@vtext.com',
                body=f'Nettest v2 {message_time}\nConnection status to server {server}: {message}')
    except Exception as e:
        log.critical('An error occurred while trying to send a message')
        log.critical(e)


def main():
    try:
        previous_status = read_status().get("status")
    except AttributeError:
        previous_status = {}
        log.info('The status dictionary was not found in the status file and will be created anew.')
    current_server_status = {}
    for server in get_server_list():
        in_alert, alert_description = do_ping(server)
        # print(server, in_alert, alert_description)
        try:
            previous_server_status = previous_status.get(server)
        except AttributeError:
            previous_server_status = {}
            log.info(f'No previous status was found for server {server}.')
        if in_alert:
            # check the status to determine what to do next
            if previous_server_status:
                # we have some kind of record of this server
                print('we have some kind of record of this server')
                if previous_server_status.get('in_alert') == True:
                    # not a new alert
                    # determine how long it's been
                    duration_since_last_notification = (datetime.datetime.utcnow() - datetime.datetime.fromisoformat(previous_server_status.get('last_notified'))).total_seconds() / 3600
                    # print(duration_since_last_notification)
                    log.debug(f'For server {server}: Duration since last notification: {duration_since_last_notification} hours')
                    if duration_since_last_notification > hours_to_wait_between_failure_notifications:
                        last_notified = datetime.datetime.utcnow().isoformat()
                        log_message = f"Connection to server {server} is still failing. The event started at {previous_server_status.get('alert_start')} UTC. The last notification was sent at {previous_server_status.get('last_notified')} UTC. A new notification will be sent."
                        log.info(log_message)
                        send_notification(server, 'Repeat alert. ' + alert_description)
                    else:
                        # do not call notification
                        last_notified = previous_server_status.get('last_notified')
                        log_message = f"Connection to server {server} is still failing. The event started at {previous_server_status.get('alert_start')} UTC. The last notification was sent at {previous_server_status.get('last_notified')} UTC. A new notification will not be sent at this time."
                        log.info(log_message)
                    alert_start = previous_server_status.get('alert_start')
                else:
                    # this is a new alert
                    alert_start = datetime.datetime.utcnow().isoformat()
                    last_notified = alert_start
                    log.info(f'New alert: Server {server} cannot be contacted. The error was {alert_description}.')
                    send_notification(server, 'New alert. ' + alert_description)
            else:
                # in alert, but we have no prior knowlege of this server
                print('we have no prior knowlege of this server')
                alert_start = datetime.datetime.utcnow().isoformat()
                last_notified = alert_start
                log.info(f'New alert: Server {server} cannot be contacted. The error was {alert_description}.')
                send_notification(server, 'New alert. ' + alert_description)
        else:
            # not in alert, or no longer in alert
            if previous_server_status:
                # we have prior knowledge
                if previous_server_status.get('in_alert') == True:
                    log.info(f'Connection to server {server} has been reestablished.')
                    send_notification(server, 'Connection reestablished.')
            alert_start = None
            last_notified = None
        current_server_status[server] = {
                "last_checked_utc": datetime.datetime.utcnow().isoformat(), 
                "last_checked_local_time": datetime.datetime.now().isoformat(), 
                "in_alert": in_alert, 
                "alert_start": alert_start,
                "alert_description": alert_description, 
                "last_notified": last_notified}

    write_status({"updated_local_time": datetime.datetime.now().isoformat(), "updated_utc": datetime.datetime.utcnow().isoformat(),"status": current_server_status})

try:
    if __name__ == '__main__':
        main()
    test_notification = False
    if test_notification:
        log.info('A test notification is being sent.')
        send_notification('test', 'testing notification only')
    LogInterface.prune(threshold=9999999999, keep=4800)
except Exception as e:
    log.critical(e)


# if __name__ == '__main__':
#     main()
# test_notification = False
# if test_notification:
#     log.info('A test notification is being sent.')
#     send_notification('test', 'testing notification only')

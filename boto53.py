#!/usr/bin/env python

 #**************************************************************************
# Copyright (C) 2006-2013 by Cyan Optics Inc.
# All rights reserved.
#                   _____
#                 /\   _ \
#                 \ \ \/\_\  __  __     __      ___
#                  \ \ \/_/_/\ \/\ \  / __`\  /   _`\
#                   \ \ \/\ \ \ \_\ \/\ \/\.\_/\ \/\ \
#                    \ \____/\/`____ \ \__/.\_\ \_\ \_\
#                     \/___/  `/___/> \/__/\/_/\/_/\/_/
#                                /\___/
#                                \/__/
#                   _____          __
#                 /\  __ \        /\ \__  __
#                 \ \ \/\ \  _____\ \  _\/\_\     ___   ____
#                  \ \ \ \ \/\  __`\ \ \/\/\ \  / ___\ /  __\
#                   \ \ \_\ \ \ \/\ \ \ \_\ \ \/\ \__//\__\
#                    \ \_____\ \ ,__/\ \__\\ \_\ \____\/\____/
#                     \/_____/\ \ \/  \/__/ \/_/\/____/\/___/
#                              \ \_\
#                               \/_/
# PROPRIETARY NOTICE
# This Software consists of confidential information.
# Trade secret law and copyright law protect this Software.
# The above notice of copyright on this Software does not indicate
# any actual or intended publication of such Software.
#
#**************************************************************************/

# NOTE FOR SETTING UP CREDENTIALS:
#
# Option #1
# Save creds in ~/.boto. Then set environment variable BOTO_CONFIG=~/.boto
#
# Option #2
# boto also will let it go in /etc/boto.cfg. This is how I use it for blueplanet sim machines.
#
# Example /etc/boto.cfg file
# [Credentials]
# aws_access_key_id = <<YOURS HERE>>
# aws_secret_access_key = <<YOURS HERE>>


from boto import connect_route53
from boto import route53
from boto.route53.record import ResourceRecordSets
from boto.route53.connection import Route53Connection
import boto.ec2
import sys
import os
import pprint
import logging
import re
from optparse import OptionParser, OptionGroup

# Credentials Option #3, for development.
# If you don't have a .boto config file, you can hard-code your creds here after
# enabling the two lines of code below.
#
# boto.config.set('Credentials', 'aws_access_key_id', 'YOURS GOES HERE')
# boto.config.set('Credentials', 'aws_secret_access_key', 'YOURS GOES HERE')

# route53 zone
zone_id = "Z2KSRKJN5W6A4A"
region = "us-east-1"
ttl = 300
def add_route53_record(name, ip_address=None):
    '''
    Pass in the name of the instance, as stored in the Name tag.
    Sets the actual IP of the instance in route 53, unless you supply your own IP address.
    '''
    route53_ip = get_route53_ip(name)
    actual_ip = get_instance_ip(name)

    logging.info("Route53 IP=%s, Actual IP=%s" % (route53_ip, actual_ip))

    if ip_address is not None:  # override allowed
        actual_ip = ip_address

    if route53 is None and actual_ip is None:
        logging.error("Invalid input supplied. HOST=%s, IP=%s " % (name, actual_ip))
        return

    if actual_ip is None:
        logging.error("Could not find IP address for %s." % (name))
        return

    if actual_ip == route53_ip:
        print "%s, IP=%s already exists." % (name, actual_ip)
    else:
        conn = connect_route53()
        changes = ResourceRecordSets(conn, zone_id)

        logging.info("DELETE %s, IP=%s, TTL=%s" % (name, route53_ip, ttl))
        logging.info("CREATE %s IP=%s, TTL=%s" % (name, actual_ip, ttl))

        if options.dryrun is True:
            return

        # Delete old record if it exists
        if route53_ip is not None:
            # NOTE: TTL is 300. But it must match in the record or this fails.
            change1 = changes.add_change("DELETE", name, "A", ttl=ttl)
            change1.add_value(route53_ip)

        #create A record
        change2 = changes.add_change("CREATE", name, "A", ttl=ttl)
        change2.add_value(actual_ip)

        result = changes.commit() # Note: If delete&create this commit does both in one transaction.

        print "Updated Route53 %s, IP=%s" % (name, actual_ip)

    return

def delete_route53_record(name):
    '''
    Deletes a record!
    '''
    # NOTICE: Our registered DNS aliases have a "pub-" prefix.
    # Our instance names do not.
    route53_ip = get_route53_ip(name)
    logging.info("%s, IP=%s" % (name, route53_ip))
    conn = connect_route53()
    changes = ResourceRecordSets(conn, zone_id)

    logging.info("DELETE %s, IP=%s, TTL=%s" % (name, route53_ip, ttl))
    if options.dryrun is True:
        return

    # Delete old record if it exists
    if route53_ip is not None:
        # NOTE: TTL is 300. But it must match in the record or this fails.
        change1 = changes.add_change("DELETE", name, "A", ttl=ttl)
        change1.add_value(route53_ip)
        result = changes.commit() # Note: If delete&create this commit does both in one transaction.
        print "Delete %s, IP=%s" % (name, route53_ip)
    else:
        print "No record match found."
    return

def get_localhost_ip():
    '''
    Only applies when running this tool directly on an EC2 instances -
    Call amazon services to fetch the public IP of the local host.
    '''
    output = os.popen("curl -s http://169.254.169.254/latest/meta-data/public-ipv4").readlines()

    if len(output) > 0:
        pattern = re.compile(r'\d{1,3}\.\d{1,3}.\d{1,3}.\d{1,3}')
        ip = output[0]
        if pattern.match(ip):  # Make sure this is an IP address
            return ip
    return None

def get_instance_ip(name):
    '''
    Return the IP of an instance that has a tag of "Name" that matches
    '''
    if options.local is True:
        print "Getting public IP of localhost..."
        return get_localhost_ip()

    # Otherwise, let's go try to find the IP from EC2, based on the Name tag = hostname.
    print "Searching EC2 region %s for %s..." % (region, name)
    conn = boto.ec2.connect_to_region(region)

    try:
        reservations = conn.get_all_instances(filters={'tag:Name':name})
        instance = reservations[0].instances[0]
        return instance.ip_address
    except:
        return None

def get_route53_ip(name):
    '''
    Returns the IP addres registerd in route53. Note: This can differ from what the actual
    IP address is if you don't use elastic. To get the actual IP address use get_instance_ip()
    '''
    conn = connect_route53()

    record_lookup = {}
    # Create a dict out of the data for easier lookup.
    for record in conn.get_all_rrsets(zone_id):
        record_lookup[record.name.rstrip('.')] = record.resource_records[0]

    if name in record_lookup.keys():
        return record_lookup[name]
    else:
        return None

if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-d", "--delete", dest="delete_name",
                      help="Delete record.")
    parser.add_option("-l", "--local", dest="local", action="store_true", default=False,
                      help="Add this option to --add when running directly on the EC2 instance for most reliable IP \
lookup.")
    parser.add_option("-a", "--add", dest="add_name",
                      help="Add a record. It will attempt to lookup the IP address from aws. \
Can run this command from any host.")
    parser.add_option("-i", "--ip",
                      dest="ip_address", default=None,
                      help="Force IP address to this value regardless of actual address")
    parser.add_option("--dryrun", default=False, help="Shows what will happen. Does not execute.",
                      action="store_true", dest="dryrun")
    parser.add_option("--log", default='ERROR', dest="loglevel",
                      help="Logging level.  Use INFO for some info, and DEBUG for a lot.")

    group1 = OptionGroup(parser, "EXAMPLE: Create record. The actual IP is retrieved \
by looking for an instance with the tag Name=<host>",
                        "./route53cli -n blueplanet9001.cyclone.cyaninc.com")
    group2 = OptionGroup(parser, "EXAMPLE: Add -i <IP> to force create an entry regardless if host is running",
                        "./route53cli -n blueplanet9001.cyclone.cyaninc.com -i 54.10.0.3")
    group3 = OptionGroup(parser, "EXAMPLE: Use --local option when running this command from the instance",
                        "./route53cli --local -a blueplanet9001.cyclone.cyaninc.com")
    group4 = OptionGroup(parser, "EXAMPLE: Delete reccord",
                        "./route53cli --delete -n blueplanet9001.cyclone.cyaninc.com")

    parser.add_option_group(group1)
    parser.add_option_group(group2)
    parser.add_option_group(group3)
    parser.add_option_group(group4)

    (options, args) = parser.parse_args()

    if options.dryrun:
        numeric_level = logging.INFO
    else:
        numeric_level = getattr(logging, options.loglevel.upper(), None)

    logging.basicConfig(format='%(levelname)s:%(message)s', level=numeric_level)

    if options.delete_name:
        delete_route53_record(options.delete_name)
    else:
        add_route53_record(options.add_name, options.ip_address)

    sys.exit(1)





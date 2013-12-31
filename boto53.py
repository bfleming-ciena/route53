#!/usr/bin/env python

# For my case, our actual public DNS aliases are pub-name.domain.
# But the actual instance itself doesn't have the pub-, i.e name.domain
# I lookup the actual IP based on the tag "Name" on the instance
#
# If we saved the same name in route53 as we do in the Name tag, then there is no
# need to have two arguments to add_route53_record.

from boto import connect_route53
from boto import route53
from boto.route53.record import ResourceRecordSets
from boto.route53.connection import Route53Connection
import boto.ec2
import sys
# your amazon keys

#secret key
access = "YOURS GOES HERE"
#access key
key  = "YOURS GOES HERE"
# route53 zone
zone_id = "YOURS GOES HERE"

def add_route53_record(dns_name, name_tag, ip_address):
    '''
    Register the DNS alias with route53
    Check if entry exists and update only if necessary
    '''

    actual_ip = get_instance_ip(name_tag)
    route53_ip = get_route53_ip(dns_name)

    if actual_ip == route53_ip:
        print "%s already exists. No change." % (actual_ip)
    else:
        print "DIFFERENT"
        conn = connect_route53(access, key)
        changes = ResourceRecordSets(conn, zone_id)

        print "Pretend delete %s %s" % (dns_name, route53_ip)
        print "Pretend create %s %s" % (dns_name, actual_ip)

        # Enable this to actuall do it.
        # delete old record
        # change = changes.add_change("DELETE", dns_name, "A")
        # change.add_value(route53_ip)
        # result = changes.commit()

        #create A record
        # change = changes.add_change("CREATE", dns_name, "A")
        # change.add_value(actual_ip)
        # result = changes.commit()

        print "Updated Route53 DNS %s > %s" % (dns_name, actual_ip)


    return


def get_instance_ip(name):
    '''
    Return the IP of an instance that has a tag of "Name" that matches
    '''
    conn = boto.ec2.connect_to_region("us-east-1", aws_access_key_id=access, \
    aws_secret_access_key=key)

    try:
        reservations = conn.get_all_instances(filters={'tag:Name':name})
        instance = reservations[0].instances[0]
        return instance.ip_address
    except:
        reservations = None
        instance = None
        return None

def get_route53_ip(name):
    '''
    Returns the IP addres registerd in route53. Note: This can differ from what the actual
    IP address is if you don't use elastic. To get the actual IP address use get_instance_ip()
    '''
    conn = connect_route53(access, key)

    record_lookup = {}

    # Create a dict to easy lookup
    for record in conn.get_all_rrsets(zone_id):
        record_lookup[record.name.rstrip('.')] = record.resource_records[0]

    if name in record_lookup.keys():
        return record_lookup[name]
    else:
        return None

if __name__ == '__main__':

    # Need to omit the -pub
    # print get_instance_ip('name.mydomain.com')
    # print get_route53_ip('pub-name.mydomain.com')
    add_route53_record('pub-name.mydomain.com','name.mydomain.com', "54.15.16.17")
    sys.exit(1)





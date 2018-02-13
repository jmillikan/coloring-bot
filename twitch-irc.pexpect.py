#!/usr/bin/python3

'''
Demonstrate what the bot *should* do to connect to (plaintext) twitch and send and recieve basic messages.

Frankly I *could* write the bot with pexpect... But that would be really janky compared to Twisted. Probably.

Symmetric with (plaintext) test.py
'''

import pexpect
import time
import argparse
import re

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("twitchbot_user", type=str)
    ap.add_argument("twitchbot_secret", type=str)
    ap.add_argument("channel", type=str)

    args = ap.parse_args()

    secret = args.twitchbot_secret
    user = args.twitchbot_user
    channel = args.channel

    esc = re.escape
    
    # p = pexpect.spawn("telnet localhost 6667")
    p = pexpect.spawn("telnet irc.chat.twitch.tv 6667")

    p.expect("Escape\\ character\\ is\\ \\'\\^\\]\\'\\.")
    
    print("Connected")

    time.sleep(1.0)
    
    p.sendline("PASS oauth:%s" % secret)
    p.sendline("NICK %s" % user)

    p.expect(".*\\:\\>")

    print("Read server greeting")

    p.sendline("JOIN %s" % channel)

    p.sendline("PRIVMSG %s :BORK BORK BORK" % channel)

    p.close()

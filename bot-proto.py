#!/usr/bin/python3

'''
Prototype bot using pexpect instead of... something good, like twisted.
'''

import pexpect
import time
import argparse
import re
import drawing

def proto_bot(secret, user, channel, table_name):

    esc = re.escape
    
    p = pexpect.spawn("telnet irc.chat.twitch.tv 6667")

    p.expect("Escape\\ character\\ is\\ \\'\\^\\]\\'\\.")
    
    print("Connected")

    time.sleep(1.0)
    
    p.sendline("PASS oauth:%s" % secret)
    p.sendline("NICK %s" % user)

    p.expect(".*\\:\\>")

    print("Read server greeting")

    p.sendline("JOIN %s" % channel)
    p.sendline("PRIVMSG %s :Prototype color-bot is awaiting commands!" % channel)

    def maintain_ping(t):
        a = p.expect(["PING \\:tmi\\.twitch\\.tv", pexpect.TIMEOUT], timeout=t)
        if a == 0:
            p.sendline("PONG :tmi.twitch.tv")
            print("Ponged in maintenance")

    lst = p.compile_pattern_list(["PING \\:tmi\\.twitch\\.tv\r\n", pexpect.TIMEOUT, "\\:(\\S+)\\!(\\S+)\\s+PRIVMSG\\s+(\\S+)\\s+\\:!(\\S+)(.*)\r\n"])
    while True:
        a = p.expect_list(lst)

        if a == 0:
            p.sendline("PONG :tmi.twitch.tv")
            print("Ponged")
        if a == 1:
            print("Timed out! Looping.")
        if a == 2:
            try:
                print("Coloring...")
                (guest_user_b, guest_host_b, send_channel_b, command_b, rest_b) = p.match.groups()
                command = command_b.decode()
                rest = rest_b.decode()
                send_channel = send_channel_b.decode()

                # Only the designated channel - no whispers or anything
                if channel == send_channel:
                    if command == "colorhelp":
                        p.sendline("PRIVMSG %s :Commands: !c #RRGGBB X, !img XYZ.png" % channel)
                    elif command == "c":
                        m = re.match("\\s+(\\S+)\\s+(\\S+)", rest)
                        if m is None:
                            print("Bad color args!")
                        else:
                            (color_s, region_s) = m.groups()
                        
                            drawing.update_region(table_name, color_s, region_s)
                    elif command == "img":
                        m = re.match("\\s+(\\S+)", rest)

                        image_name, = m.groups()

                        drawing.update_image(table_name, image_name)
                    else:
                        print("Unknown command %s" % command)
            except Exception as e:
                print("Error: %s" % str(e))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("twitchbot_user", type=str)
    ap.add_argument("twitchbot_secret", type=str)
    ap.add_argument("channel", type=str)
    ap.add_argument("table_name", type=str)

    args = ap.parse_args()

    proto_bot(args.twitchbot_secret, args.twitchbot_user, args.channel, args.table_name)


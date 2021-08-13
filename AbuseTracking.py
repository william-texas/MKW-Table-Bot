'''
Created on Aug 5, 2021

@author: willg
'''
import discord
from discord.ext import tasks
import common
import UserDataProcessing
import UtilityFunctions
import TableBotExceptions
from collections import defaultdict
from datetime import datetime

bot_abuse_tracking = defaultdict(lambda: [0, [], [], False])
blacklisted_command_count = defaultdict(int)

BOT_ABUSE_REPORT_CHANNEL = None

WARN_MESSAGES_PER_SECOND_RATE = .45
BAN_RATE_MESSAGES_PER_SECOND = .48
MIN_MESSAGES_NEEDED_BEFORE_WARN = 6
MIN_MESSAGES_NEEDED_BEFORE_BAN = 8

def is_hitting_warn_rate(author_id):
    num_messages_sent = len(bot_abuse_tracking[author_id][1])
    total_message_span = bot_abuse_tracking[author_id][2][-1] - bot_abuse_tracking[author_id][2][0]
    
    if num_messages_sent < MIN_MESSAGES_NEEDED_BEFORE_WARN:
        return False
    
    rate_of_messages = num_messages_sent / total_message_span.total_seconds()
    
    return rate_of_messages > WARN_MESSAGES_PER_SECOND_RATE
        

def is_hitting_ban_rate(author_id):
    num_messages_sent = len(bot_abuse_tracking[author_id][1])
    total_message_span = bot_abuse_tracking[author_id][2][-1] - bot_abuse_tracking[author_id][2][0]
    
    if num_messages_sent < MIN_MESSAGES_NEEDED_BEFORE_BAN:
        return False
    
    rate_of_messages = num_messages_sent / total_message_span.total_seconds()
    return rate_of_messages > BAN_RATE_MESSAGES_PER_SECOND
    
    


async def abuse_track_check(message:discord.Message):
    
    author_id = message.author.id
    bot_abuse_tracking[author_id][0] += 1
    bot_abuse_tracking[author_id][1].append(message.content)
    bot_abuse_tracking[author_id][2].append(datetime.now())
    messages_sent = bot_abuse_tracking[author_id][1]
    if is_hitting_ban_rate(author_id) and bot_abuse_tracking[author_id][3]: #certain spam and we already warned them
        UserDataProcessing.add_Blacklisted_user(str(author_id), "Automated ban - you spammed the bot. This hurts users everywhere because it slows down the bot for everyone. You can appeal in 1 week to a bot admin or in Bad Wolf's server.")
        if BOT_ABUSE_REPORT_CHANNEL is not None:
            to_send = f"Automatic ban for spamming bot:\nDiscord: {str(message.author)}\nDiscord ID: {author_id}\nDisplay name: {message.author.display_name}\nDiscord Server: {message.guild}\nDiscord Server ID: {message.guild.id}\nMessages Sent:"
            messages_to_send_back = UtilityFunctions.chunk_join([to_send] + messages_sent)
            for message_to_send in messages_to_send_back:
                await BOT_ABUSE_REPORT_CHANNEL.send(message_to_send)
        raise TableBotExceptions.BlacklistedUser("blacklisted user")
    if is_hitting_warn_rate(author_id) and not bot_abuse_tracking[author_id][3]: #potential spam, warn them if we haven't already
        bot_abuse_tracking[author_id][3] = True
        await message.channel.send(f"{message.author.mention} slow down, you're sending too many commands. To avoid getting banned, wait 5 minutes before sending another command.")
        to_send = f"The following users were warned:\nDiscord: {str(message.author)}\nDiscord ID: {author_id}\nDisplay name: {message.author.display_name}\nDiscord Server: {message.guild}\nDiscord Server ID: {message.guild.id}\nMessages Sent:"
        messages_to_send_back = UtilityFunctions.chunk_join([to_send] + messages_sent)
        for message_to_send in messages_to_send_back:
            await BOT_ABUSE_REPORT_CHANNEL.send(message_to_send)

    return True

#Raises BlacklistedUser Exception if the author of the message is blacklisted
#Sends a notification once in a while that they are blacklisted
async def blacklisted_user_check(message:discord.Message, notify_threshold=15):
    author_id = message.author.id
    if str(author_id) in UserDataProcessing.blacklisted_Users:
        if blacklisted_command_count[author_id] % notify_threshold == 0:
            await message.channel.send("You have been blacklisted by a bot admin. You are not allowed to use this bot. Reason: " + str(UserDataProcessing.blacklisted_Users[str(author_id)]))
        blacklisted_command_count[author_id] += 1
        raise TableBotExceptions.BlacklistedUser("blacklisted user")
    return True

def set_bot_abuse_report_channel(client):
    global BOT_ABUSE_REPORT_CHANNEL
    BOT_ABUSE_REPORT_CHANNEL = client.get_channel(common.BOT_ABUSE_REPORT_CHANNEL_ID)
    
#Every 120 seconds, checks to see if anyone was "spamming" the bot and notifies a private channel in my server
#Of the person(s) who were warned
#Also clears the abuse tracking every 60 seconds
async def check_bot_abuse():
    abuserIDs = set()
    
    for user_id, message_count in bot_abuse_tracking.items():
        if message_count[0] > common.SPAM_THRESHOLD:
            if str(user_id) not in UserDataProcessing.blacklisted_Users:
                abuserIDs.add(str(user_id))
    bot_abuse_tracking.clear()
    
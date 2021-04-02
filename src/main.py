import discord
import time
import discord.utils
import boto3
import os
from role_dict import chars

def lambda_handler(event, context):

    # define clients, env vars etc.
    ddb = boto3.client('dynamodb')
    ssm = boto3.client('ssm')
    client = discord.Client()
    env = os.environ['Env']
    bot_token = ssm.get_parameter(Name=f'{env}-discord-fighter-bot-token', WithDecryption=True)['Parameter']['Value']
    table_name = os.environ['TableName']

    # bot commands. reminder to avoid clashing with other bots
    help_commands = ('.help', '.commands', '!commands')
    role_commands = ('.role', '.getrole', '!getrole')
    match_commands = ('.mm', '!mm')

    # function definitions

    # function to add and remove roles from players
    async def role(message):
        role_names = [] # generate list of current role names
        for role in message.author.roles:
            role_names.append(role.name)
        # immediately look for role string
        role_string = message.content.split('role ')[1] # split string at role and get what user typed after. covers `.getrole` and `.role`
        if len(role_string) < 3: # discard invalid role strings
            await message.channel.send(content='Not recognised as an available role; please retry. ')
            return
        # check player's current roles
        current_role_names = []
        for role in message.author.roles:
            current_role_names.append(role.name)
        # check for the possible terms to look for
        selected_role_name = 'blank' # in case nothing found
        for char in chars:
            for term in char['Terms']:
                if term.lower() in role_string.lower(): # add lower to both to prevent case problems
                    selected_role_name = char['Character']
                    break
            else: # https://stackoverflow.com/questions/189645/how-to-break-out-of-multiple-loops
                continue
            break
        if selected_role_name == 'blank': # ie if nothing found
            await message.channel.send(content='Not recognised as an available role; please retry. ')
            return
        elif selected_role_name in role_names: # only do this if we find in list of role names
            for role in message.author.roles:
                if selected_role_name in role.name:
                    await message.author.remove_roles(role)
                    await message.channel.send(content=f'Removed role {selected_role_name} from {message.author}. ')
                    break
        else: # add role
            # get role with name from server
            role = discord.utils.get(message.author.guild.roles, name=selected_role_name)
            await message.author.add_roles(role)
            await message.channel.send(content=f'Added role {selected_role_name} for {message.author}. ')

    # function to @ 2 players who have entered matchmaking queue
    async def match(message):
        # get queue and look for expired items
        queue = ddb.scan(TableName=table_name)['Items']
        for m in queue: # for each message in the queue
            if time.time() >= float(m['Time']['N']): # timestamp is stored as an expiration time in epoch format, so if the current time is equal to or greater than that time,
                ddb.delete_item(TableName=table_name,Key={'Author': m['Author']}) # expire the message
        player_refreshed = False # default false, will change to true to avoid extra messages when player refrehses
        for m in queue:
            if int(m['Author']['S']) == message.author.id: # check if author already in queue. if so, remove
                print(f'{message.author} is already queued; removing old entry. ')
                player_refreshed = True # for later use
                ddb.delete_item(TableName=table_name,Key={'Author': {'S': str(message.author.id)}})
        if 'cancel' in message.content:
            print(f'{message.author} has requested to cancel; not adding new entry. ')
            await message.channel.send(content=f'{message.author} has been removed from the queue. ')
        else:
            # format message
            format_message = {}
            format_message['author'] = message.author.id
            format_message['timestamp'] = time.time()
            # find time in message if specified
            try:
                mins = round(float(message.content.split()[1])) # removes whitespace, takes number that should be after `.mm`, rounds it and converts to int
                if mins > 120:
                    mins = 120
                elif mins < 5:
                    mins = 5
            except:
                mins = 30
            # add timeout to timestamp, effectively making it an expiration time
            format_message['timestamp'] = format_message['timestamp'] + (mins * 60)
            # regardless of whether the author had an old message removed from queue or not, add their new message to the end
            ddb.put_item(TableName=table_name,Item={'Author': {'S': str(format_message['author'])}, 'Time': {'N': str(format_message['timestamp'])}})
            print(f'{message.author} has been added to queue. ')
            # notify channel adding author to queue
            if player_refreshed == False: # don't do a duplicate message if they were already told they refreshed
                await message.channel.send(content=f'{message.author} has been added to the matchmaking queue for {mins} minutes. ')
            else:
                await message.channel.send(f'{message.author} is already in the queue; refreshing timeout ({mins} minutes). ')
            # now check the queue length, get queue again from ddb
            queue = ddb.scan(TableName=table_name)['Items']
            if len(queue) > 1:
                # pit the first two members of the queue against one another
                announce = f"<@{queue[0]['Author']['S']}> vs <@{queue[1]['Author']['S']}>: Fight! "
                print(f"{queue[0]['Author']['S']} and {queue[1]['Author']['S']} have been matched. They will be removed from the queue. ")
                # clear those authors
                ddb.delete_item(TableName=table_name,Key={'Author': {'S': queue[0]['Author']['S']}})
                ddb.delete_item(TableName=table_name,Key={'Author': {'S': queue[1]['Author']['S']}})
                # send message to channel that the second challenger sent the '.mm' message in
                await message.channel.send(content=announce)

    # read messages in chat to determine if they have commands for the bot and respond accordingly
    @client.event # aka on_message = client.event(on_message)
    async def on_message(message):
        # if the message has the correct syntax, evaluate further
        if message.content.startswith(help_commands):
            mm_help_string = 'Commands: \n- `.mm` adds you to the matchmaking queue. You can optionally specify a timeout in minutes with `.mm mins`; for example, `.mm 120`. \nThe timeout can be between 5 and 120 minutes. If no timeout is specified, the timeout will default to 30 minutes. If you re-enter this command while still in the queue, your timeout will be changed, not incremented. You can remove yourself from the queue, however, with `.mm cancel`. \n'
            role_help_string = '- `.role role` gives you the specified role if you don\'t have it, or removes it if you do. \n'
            generic_help_string = ' -`.help` displays this message again. '
            await message.channel.send(content=mm_help_string + role_help_string + generic_help_string)

        elif message.content.startswith(role_commands):
            await role(message)

        elif message.content.startswith(match_commands):
            await match(message)

        time.sleep(1)

    # intialisation event
    @client.event
    async def on_ready():
        # status message for bot
        await client.change_presence(activity=discord.Game(name='.help for commands', type=0))
        print('Running as ' + client.user.name + ' (' + str(client.user.id) + ')... ')

    client.run(bot_token.strip())

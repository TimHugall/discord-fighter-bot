# discord-fighter-bot
A Serverless Discord bot to organise games and designate roles for Discord fighters

# Requirements
- Terraform 0.14
- Python 3.8.7

# Instructions

1. Create two Discord bot tokens
2. Fork the repo
3. Create two environments in repo: _dev_ and _prod_. Set up prod for continuous delivery rather than deployment; there's a step to destroy the dev environment after prod deploys. 
4. Create the following repository secrets:
    - `AWS_ACCESS_KEY_ID`
    - `AWS_REGION`
    - `AWS_SECRET_ACCESS_KEY`
    - `DEV_DISCORD_BOT_TOKEN`
    - `PROD_DISCORD_BOT_TOKEN`
5. Create an additional repository secret entitled `CHARS`, containing something like:
```
chars = [
    {'Character': 'Role Name on Server', 'Terms': ['serve']},
    {'Character': 'Another Role Name on Server', 'Terms': ['another', 'server']},
]
```
`Terms` is a list of search terms that can be entered to obtain a role. Order your list correctly to ensure that roles are evaluated in the order you want. 
6. Edit `backend.tf` and `versions.tf` to meet your requirements. 

# To Do
- Code cleanup
- More exception handling

## Improvements / Limitations
- By design, this function runs every ~15 minutes on a schedule, storing queue data in DynamoDB in between runs. There is a small gap between invocations during which the bot is down. Potentially its timeout / schedule can be tweaked to minimise this.
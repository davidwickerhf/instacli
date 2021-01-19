import json
import logging

from instaclient.instagram.profile import Profile
from instacli.models.igclient import IGClient
from click.termui import progressbar
import click
from .models import *

@click.group()
def instacli():
    """A wrapper for the instaclient package"""
    
@instacli.command()
@click.option('-dp', '--driverpath', type=click.Path(exists=True),
default=lambda: Settings().driver_path, required=False, help="The path to the web driver executable.")
@click.option('-dv', '--drivervisible', type=click.BOOL,default=lambda: Settings().driver_visible,  required=False, help="Set the visibility of the chromedriver.")
@click.option('-l', '--logging', type=click.BOOL, default=lambda: Settings().logging, help="Set visibility of log messages")
@click.option('-op', '--outputpath', type=click.Path(exists=True, dir_okay=True),
default=lambda: Settings().output_path, required=False, help="The path to for the output JSON files")
def settings(driverpath, drivervisible, logging, outputpath):
    """Customize your instacli settings"""
    settings:Settings = Settings()
    if driverpath != settings.driver_path:
        settings.set_driver_path(driverpath)
    if drivervisible != settings.driver_visible:
        settings.set_driver_visible(drivervisible)
    if logging != settings.logging:
        settings.set_logging(logging)
    if outputpath != settings.output_path:
        settings.set_output_path(outputpath)


@instacli.command()
@click.option('--login', type=click.STRING, help='The instagram username to use for the scrape.', default=None)
@click.option('--password', type=click.STRING, hide_input=True, help="The password of the IG account you are using for the scrape.", default=None)
@click.option('--followers', is_flag=True, default=False, help="Use this flag to scrape the user's followers.")
@click.option('--following', is_flag=True, default=False, help="Use this flag to scrape the user's following.")
@click.option('--target', required=True, type=click.STRING, help="The username of the user to scrape.")
@click.option('--count', required=True, type=click.IntRange(1, 10000), help="The amount of data to scrape.")
@click.option('--cursor', type=click.STRING, help="GraphQL end cursor to resume the scrape with.", default=None)
@click.option('--output', type=click.Path(exists=True, dir_okay=True), help="The path to the folder where you wish the JSON output to be saved to.")
def getinfo(login, password, followers, following, target, count, cursor, output):
    """Scrape a user's followers or following
    
    The scraped users will be saved in a json file. The JSON output will also contain the last used cursor for the scraping pagination."""

    if not followers and not following:
        click.echo("To execute this command you must insert the flags --following or --followers.")
        return

    if login and not password:
        click.echo(f"If you are using the --login option, you must provide a password as well with the --password option")
        return

    settings = Settings()
    if not settings.driver_path:
        click.echo("No path for the chromedriver defined. Please define it using: instacli settings -dp [...]")
        return

    if not output and not settings.output_path:
        click.echo("No output specified in command nor in settings. Please specify it with --output")
        return

    if not output:
        output = settings.output_path

    def scrape_callback(scraped:list, progress:Progress):
        progress.update_progress(len(scraped))

    bar = progressbar(length=count)
    progress = Progress(bar)

    client = IGClient()
    client.login(login, password)
    client.set_logger_level(level=logging.WARNING)
    if followers:
        # Scrape Followers
        extension = 'followers'
        try:
            users, newcursor = client.get_followers(target, count, end_cursor=cursor, callback=scrape_callback, callback_frequency=5, progress=progress)
        except Exception as error:
            client.disconnect()
            click.secho(f"\nError: {error.message}", fg='red')
            return
    else:
        # Scrape Following
        extension = 'following'
        try:
            users, newcursor = client.get_following(target, count, end_cursor=cursor, callback=scrape_callback, callback_frequency=10, progress=progress)
        except Exception as error:
            client.disconnect()
            click.secho(f"\nError: {error.message}", fg='red')
            return

    # Save Info
    with open(f'{output}/{target}-{extension}.json', 'r+') as file:
        data = json.load(file)
        old = list()
        if data.get('data') or data.get('cursor'):
            if isinstance(data.get('data'), list):
                for item in data.get('data'):
                    old.append(Profile.de_json(item, client))
        for user in old:
            if user not in users:
                users.append(user)

    serialized = list()
    for user in users:
        serialized.append(user.to_dict())

    with open(f'{output}/{target}-{extension}.json', 'w') as file:
        json.dump({'cursor': newcursor, 'data': serialized}, file)

    click.secho(f"\n{len(users)} scraped users saved to {output}/{target}:{extension}.json", fg='green')
    return serialized


if __name__ == '__name__':
    instacli(prog_name='instacli')

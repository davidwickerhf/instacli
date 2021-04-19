import io, re, os
from pathlib import WindowsPath
from random import random
import json, csv
import logging, shutil
import time
import datetime
from typing import List, Literal
from instaclient.errors.common import FollowRequestSentError, InstaClientError, InvalidUserError
from instaclient.instagram.hashtag import Hashtag
from instaclient.instagram.post import Post
from webdrivermanager import ChromeDriverManager
from instaclient.instagram.profile import Profile
import requests
from instacli.models.igclient import IGClient
from click.termui import progressbar
import click
from .models import *


def chromedriver():
    settings:Settings = Settings()
    if not settings.driver_path:
        result = click.confirm("Do you wish to install the appropriate Chromedriver? (Make sure to have Chrome installed first)", default=True, abort=True)

        try:
            path:WindowsPath = ChromeDriverManager().download_and_install()[0]
            settings.set_driver_path(str(path))

            return True
        except:
            click.secho("There was an issue when installing the chromedriver. Please try again or specify the path for a custom chromedriver with: instacli settings -dp [PATH TO CHROMEDRIVER]", fg='red')
            return False
    return True




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
        
    print_settings = True
    if driverpath != settings.driver_path:
        settings.set_driver_path(driverpath)
        print_settings = False
    if drivervisible != settings.driver_visible:
        settings.set_driver_visible(drivervisible)
        print_settings = False
    if logging != settings.logging:
        settings.set_logging(logging)
        print_settings = False
    if outputpath != settings.output_path:
        settings.set_output_path(outputpath)
        print_settings = True
    
    if print_settings:
        click.echo(f"Settings: {vars(settings)}")


@instacli.command()
@click.option('--login', type=click.STRING, help='The instagram username to use for the scrape.', required=True)
@click.option('--password', type=click.STRING, hide_input=True, help="The password of the IG account you are using for the scrape.", required=True)
@click.option('--followers', is_flag=True, default=False, help="Use this flag to scrape the user's followers.")
@click.option('--following', is_flag=True, default=False, help="Use this flag to scrape the user's following.")
@click.option('--target', required=True, type=click.STRING, help="The username of the user to scrape.")
@click.option('--deepscrape', required=False, is_flag=True, default=False, help="Use this flag to deep scrape (will require more time)")
@click.option('--count', required=True, type=click.IntRange(1, 10000), help="The amount of data to scrape.")
@click.option('--cursor', type=click.STRING, help="GraphQL end cursor to resume the scrape with.", default=None)
@click.option('--output', type=click.Path(exists=True, dir_okay=True), help="The path to the folder where you wish the JSON output to be saved to.")
@click.option('--csvfile', required=False, is_flag=True, help="Will output the scraped data as a CSV file. Defaults to a JSON file.")
@click.option('--onlybusiness', required=False, is_flag=True, help="Scrape only business accounts" )
@click.option('--onlyprivate', required=False, is_flag=True, help="Scrape only private accounts" )
@click.option('--onlypublic', required=False, is_flag=True, help="Scrape only public accounts" )
@click.option('--onlyverified', required=False, is_flag=True, help="Scrape only veridied accounts" )
def getinfo(login, password, followers, following, target, deepscrape, count, cursor, output, onlybusiness, onlyprivate, onlypublic, onlyverified, csvfile):
    """Scrape a user's followers or following
    
    The scraped users will be saved in a json file. The JSON output will also contain 
    the last used cursor for the scraping pagination.

    The output will be saved in a .json file inside the folder specified by --output.
    The naming of the .json file will be consistent with the following format:
    "timestamp-target-action.json", where "timestamp" is the timestamp of the launch
    of the command, "target" is the user you are getting info on and action is defined by
    the flags "--followers" or "--following"
    """
    if not chromedriver():
        return

    # If verified, also public
    # If business, also public

    # NO onlybusiness + onlyprivate
    # NO onlypublic + onlyprivate
    # NO onlyverified + onlyprivate

    # SI onlypublic + onlybusiness
    # SI onlypublic + onlyverified

    if onlyprivate:
        if onlybusiness or onlypublic or onlyverified:
            click.secho('You can\' select --onlyprivate along with --onlypublic, --onlybusiness or --onlyverified', fg='red')
            return
    
    timestamp = int(time.time())
    if not followers and not following:
        click.echo("To execute this command you must insert the flags --following or --followers.")
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
    users:List[Profile] = list()

    # SOFT SCRAPE
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
    

    # APPLY FILTERS
    filtered = list()
    if onlyprivate:
        flag = 'onlyprivate'
        for user in users:
            if user.is_private:
                filtered.append(user)
    elif onlypublic:
        flag = 'onlypublic'
        for user in users:
            if not user.is_private:
                filtered.append(user)
    elif onlyverified:
        flag = 'onlyverified'
        for user in users:
            if user.is_verified:
                filtered.append(user)
    else:
        flag = 'all'
        filtered = users
    users = filtered


    # DEEP SCRAPE
    if deepscrape or onlybusiness:
        try:
            todo = list()
            if onlybusiness:
                for user in users:
                    if not user.is_private:
                        todo.append(user)
            else:
                todo = users

            deepscraped = list()
            failed = list()
            click.secho(f"\nStarting to deep scrape {len(todo)} users")
            bar = progressbar(length=len(todo))
            progress = Progress(bar)

            for index, user in enumerate(todo):
                try:
                    profile = user.refresh()
                    if not profile:
                        raise InvalidUserError(user.username)
                    deepscraped.append(profile)
                    progress.update_progress(index+1)
                except InstaClientError: # TODO 
                    pass
                except:
                    failed.append(user.username)
                    deepscraped.append(user)

            users = deepscraped
            message = f"\nFinished deep scraping."
            if (len(failed) > 0):
                message += f" {len(failed)} failed - fell back to thin scrape data"
            click.secho(message, fg='green')
        except Exception as error:
            print()
            print(error)
            click.secho("There was an error", fg='red')

    # FILTER BUSINESS ACCOUNTS
    if onlybusiness:
        flag = 'onlybusiness'
        business = list()
        for user in users:
            if user.is_business_account:
                business.append(user)
        users = business
    client.disconnect()

    if len(users) == 0:
        click.secho("No users matched the selected criteria.", fg='red')
        return


    # Save Info
    serialized = list()
    for user in users:
        serialized.append(user.to_dict())

    filetype = 'csv' if csvfile else 'json'
    filename = f'{output}/{timestamp}-{target}-{extension}-{flag}.{filetype}'
    
    if csvfile:
        columns = list(vars(users[0]).keys())
        columns.remove('client')
        columns.append('cursor')

        rows = list()
        for user in users:
            data = list()
            for var in columns:
                data.append(user.to_dict().get(var))
                if var == 'cursor':
                    data.append(newcursor)
            rows.append(data)

        with open(filename, 'w+', encoding="utf-16", newline='') as file:
            writer = csv.writer(file, delimiter='\t')
            writer.writerow(columns)
            writer.writerows(rows)
    else:
        with open(filename, 'w') as file:
            json.dump({'cursor': newcursor, 'data': serialized}, file)

    click.secho(f"\n{len(users)} scraped users saved to {output}\{timestamp}-{target}-{extension}-{flag}.{filetype}", fg='green')
    return serialized



@instacli.command()
@click.option('--login', type=click.STRING, help='The instagram username to use for the scrape.', required=True)
@click.option('--password', type=click.STRING, hide_input=True, help="The password of the IG account you are using for the scrape.", required=True)
@click.option('--target', required=True, type=click.STRING, help="The username of the user to scrape.")
@click.option('--count', required=True, type=click.IntRange(1, 10000), help="The amount of data to scrape.")
@click.option('--analyze', required=False, is_flag=True, default=False, help="Use this flag to analyze hashtag (will require more time)")
@click.option('--deepscrape', required=False, is_flag=True, default=False, help="Use this flag to deep scrape Hashtags(will require more time)")
@click.option('--output', type=click.Path(exists=True, dir_okay=True), help="The path to the folder where you wish the JSON output to be saved to.")
def hashtag(login, password, target, count, analyze, output, deepscrape):
    """Scrape the posts that contain a certain Hashtag
    """
    if not chromedriver():
        return

    timestamp = int(time.time())

    settings = Settings()
    if not settings.driver_path:
        click.echo("No path for the chromedriver defined. Please define it using: instacli settings -dp [...]")
        return

    if not output and not settings.output_path:
        click.echo("No output specified in command nor in settings. Please specify it with --output")
        return

    if not output:
        output = settings.output_path

    if analyze:
        try:
            os.mkdir(output + f'\{timestamp}-{target}')
        except:
            pass
        if os.path.isdir(output):
            output += f'\{timestamp}-{target}'
            
        

    def scrape_callback(scraped:list, progress:Progress):
        progress.update_progress(len(scraped))

    bar = progressbar(length=count*2)
    progress = Progress(bar)

    client = IGClient()
    client.login(login, password)
    client.set_logger_level(level=logging.ERROR)
    posts:List[Profile] = list()

    try:
        postscodes:List[Post] = client.get_hashtag_posts(target, count, callback=scrape_callback, callback_frequency=10, progress=progress)
        for shortcode in postscodes:
            try:
                posts.append(client.get_post(shortcode))
                scrape_callback(len(posts)+len(postscodes), progress=progress)
            except:
                pass
    except Exception as error:
        client.disconnect()
        click.secho(f"\nError: {error.message}", fg='red')
        return

    if len(posts) == 0:
        click.secho("No users matched the selected criteria.", fg='red')
        return
    else:
        click.echo("\nScraped Posts... Serializing...")

    # Save Info
    serialized = list()
    for post in posts:
        serialized.append(post.to_dict())

    filename = f'{output}\{timestamp}-{target}-{count}-posts.csv'
    
    columns = list(vars(posts[0]).keys())
    columns.insert(0, 'url')
    columns.insert(1, 'hashtags')
    columns.remove('client')

    rows = list()
    allhashtags = dict()
    for post in posts:
        data = list()

        # Find hashtags
        matches = list()
        if post.caption:
            matches = re.findall(r"#\w+", post.caption)
            for hashtag in matches:
                hashtag = hashtag.replace('#','')
                if not allhashtags.get(hashtag):
                    allhashtags[hashtag] = 0
                allhashtags[hashtag] = allhashtags[hashtag] + 1

        for var in columns:
            if var == 'location' and post.location:
                data.append(post.location.slug)
            elif var == 'hashtags':
                data.append(str(matches).replace("'", '').replace("[", '').replace("]", ''))
            elif var == 'url':
                data.append(f'https://www.instagram.com/p/{post.shortcode}/')
            else:
                data.append(post.to_dict().get(var))
        rows.append(data)

    with open(filename, 'w+', encoding="utf-16", newline='') as file:
        writer = csv.writer(file, delimiter='\t')
        writer.writerow(columns)
        writer.writerows(rows)

    click.secho(f"\n{len(posts)} scraped posts saved to {filename}", fg='green')


    # HASHTAG ANALYTICS
    tags = list()
    if analyze:
        click.echo(f"Analyzing {len(allhashtags.keys())} hashtags...")

        # Save to CSV
        filename = f'{output}\{timestamp}-{target}-analysis.csv'
        columns = list()
        columns.insert(0, 'hashtag')
        columns.insert(1, 'found')            

        if deepscrape:
            bar = progressbar(length=len(allhashtags.keys()))
            progress = Progress(bar)

            for index, hashtag in enumerate(list(allhashtags.keys())):
                try:
                    tag:Hashtag = client.get_hashtag(hashtag)
                    tags.append(tag)
                    progress.update_progress(index)
                except Exception as error:
                    pass

            columns.extend(list(vars(tags[0]).keys()))
            columns.remove('client')
    
        rows = list()
        for tag in allhashtags:
            data = list()

            for var in columns:
                if var == 'hashtag':
                    data.append(tag)
                elif var == 'found':
                    data.append(allhashtags.get(tag))
                else:
                    for x in tags:
                        if x.name == tag:
                            data.append(x.to_dict().get(var))
            rows.append(data)

        with open(filename, 'w+', encoding="utf-16", newline='') as file:
            writer = csv.writer(file, delimiter='\t')
            writer.writerow(columns)
            writer.writerows(rows)

        click.secho(f"Hashtag analysis saved to {filename}", fg='green')



@instacli.command()
@click.option('--login', type=click.STRING, help='The instagram username to use for the scrape.', required=True)
@click.option('--password', type=click.STRING, hide_input=True, help="The password of the IG account you are using for the scrape.", required=True)
@click.option('--target', required=True, type=click.STRING, help="The username of the user to scrape.")
@click.option('--count', required=True, type=click.IntRange(1, 10000), help="The amount of data to scrape.")
@click.option('--start', required=False, default=None, help="The start of the date range for the scraped posts ( dd/mm/yyy )", type=click.STRING)
@click.option('--end', required=False, default=None, help="The end of the date range for the scraped posts ( dd/mm/yyyy )", type=click.STRING)
@click.option('--minlikes', required=False, default=None, help="The minimum required likes of the post", type=click.INT)
@click.option('--output', type=click.Path(exists=True, dir_okay=True), help="The path to the folder where you wish the JSON output to be saved to.")
def posts(login, password, target, count, start, end, minlikes, output):
    """Scrape and Download a user's posts.

    You can specify a date range for the scraped posts.
        By inserting only the end date ( --end ), the tool will scrape
        posts pubblished up before the specified date.
        By inserting only the start date ( --start ), the tool will scrape
        posts that were pubblished after such date

    The further in the past the start date and end date are set to,
        the longer the bot will take to retrieve such posts.
    """
    if not chromedriver():
        return

    # instacli posts --login testingwidevs --password Test2017 --target davidwickerhf --count 5 --minlikes 200 --end 27/09/2019
    timestamp = int(time.time())
    if start or end:
        while True:
            if start:
                try:
                    startdate = int(datetime.datetime.strptime(start, "%d/%m/%Y").timestamp())
                    if startdate > timestamp:
                        raise ValueError(startdate)

                    if not end:
                        break
                except:
                    start = click.prompt("The inserted Start Date is invalid or in the future. Insert it again ( dd/mm/yyyy )")
                    continue

            if end:
                try:
                    enddate = int(datetime.datetime.strptime(end, "%d/%m/%Y").timestamp())
                    if enddate > timestamp:
                        raise ValueError(enddate)

                    if start: 
                        if enddate <= startdate:
                            raise ValueError(enddate)

                    break
                except:
                    end = click.prompt("The inserted End Date is invalid or in the future. Insert it again ( dd/mm/yyyy )")
                    continue

    text = f"Looking for {count} posts"
    if minlikes:
        text += f" with a minimun of {minlikes} likes"
    if start:
        text += f", posted after {start}"
    if end:
        text += f", posted before {end}"
    click.secho(text, fg='green')

    settings = Settings()
    if not settings.driver_path:
        click.echo("No path for the chromedriver defined. Please define it using: instacli settings -dp [...]")
        return

    if not output and not settings.output_path:
        click.echo("No output specified in command nor in settings. Please specify it with --output")
        return

    if not output:
        output = settings.output_path

    try:
        os.mkdir(output + f'\{timestamp}-{target}')
    except:
        pass
    if os.path.isdir(output):
        output += f'\{timestamp}-{target}'
            
    def scrape_callback(scraped:list, progress:Progress):
        progress.update_progress(len(scraped))

    
    client = IGClient()
    client.login(login, password)
    client.set_logger_level(level=logging.ERROR)
    click.secho(f"Starting scrape...", fg='green')

    bar = progressbar(length=count)
    progress = Progress(bar)

    posts:List[Post] = list()
    scraped:List[Post] = list()
    progress.update_progress(1)

    try:
        profile = client.get_profile(target)
        range = 1
        loop = True

        while loop:
            postscodes:List[Post] = profile.get_posts(count*range)

            for shortcode in postscodes:
                try:
                    if shortcode not in [post.shortcode for post in scraped]:
                        # APPLY FILTERS
                        post = client.get_post(shortcode)
                        scraped.append(post)
                        if (minlikes and post.likes_count >= minlikes) or not minlikes:
                            if not start or post.timestamp >= startdate: 
                                if not end or post.timestamp <= enddate:
                                    posts.append(post)
                                    progress.update_progress(len(posts))
                        if len(posts) >= count:
                            loop = False
                            break
                        if startdate and post.timestamp < startdate:
                            loop = False
                            break
                except:
                    pass

            if len(posts) >= count:
                loop = False

            if len(postscodes) >= profile.post_count:
                loop = False

            range *= 2
    except Exception as error:
        client.disconnect()
        click.secho(f"\nError: {error.message}", fg='red')
        return

    if len(posts) == 0:
        click.secho("No users matched the selected criteria.", fg='red')
        return
    else:
        click.secho(f"\nScraped {len(posts)} matching Posts... Downloading...", fg='green')


    # DOWNLOAD POSTS
    bar = progressbar(length=len(posts))
    progress = Progress(bar)

    for index, post in enumerate(posts):
        if not post.media:
            continue

        for media in post.media:
            with open(f'{output}\{post.owner}-{post.timestamp}-{media.shortcode}.jpg', 'wb') as file:
                response = requests.get(media.src_url, stream=True)

                if not response.ok or response.status_code != 200:
                    continue

                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, file)
        progress.update_progress(index+1)
        time.sleep(0.5)


    # SAVE POSTS INFO
    # Save Info
    filename = f'{output}\{timestamp}-{target}-{count}-posts.csv'
    
    columns = list(vars(posts[0]).keys())
    columns.insert(0, 'url')
    columns.remove('client')

    rows = list()
    for post in posts:
        data = list()

        for var in columns:
            if var == 'location' and post.location:
                data.append(post.location.slug)
            elif var == 'url':
                data.append(f'https://www.instagram.com/p/{post.shortcode}/')
            else:
                data.append(post.to_dict().get(var))
        rows.append(data)

    with open(filename, 'w+', encoding="utf-16", newline='') as file:
        writer = csv.writer(file, delimiter='\t')
        writer.writerow(columns)
        writer.writerows(rows)

    click.secho(f"\n{len(posts)} scraped posts saved to {filename}", fg='green')
    


@instacli.command()
@click.option('--login', type=click.STRING, help='The instagram username to use for the scrape.', required=True)
@click.option('--password', type=click.STRING, hide_input=True, help="The password of the IG account you are using for the scrape.", required=True)
@click.option('--target', required=True, type=click.STRING, help="The username of the user to scrape.")
@click.option('--output', type=click.Path(exists=True, dir_okay=True), help="The path to the folder where you wish the JSON output to be saved to.")
def follow(login, password, target, output):
    """Follow a specified user
    
    The response of this action will be saved in a dedicated JSON file in the 
    specified output folder.

    The output will be saved in a .json file inside the folder specified by ``--output``.
    The naming of the .json file will be consistent with the following format:
    ``timestamp-target-action.json``, where ``timestamp`` is the timestamp of the launch
    of the command, ``target`` is the user you are getting info on and ``action`` will be ``follow``.
    """
    if not chromedriver():
        return

    timestamp = int(time.time())
    settings = Settings()
    if not settings.driver_path:
        click.echo("No path for the chromedriver defined. Please define it using: instacli settings -dp [...]")
        return

    if not output and not settings.output_path:
        click.echo("No output specified in command nor in settings. Please specify it with --output")
        return

    if not output:
        output = settings.output_path

    client = IGClient()
    client.login(login, password)
    try:
        profile = client.get_profile(target)
        if not profile:
            raise InvalidUserError(target)
        try:
            profile.follow()
        except FollowRequestSentError:
            pass
        user = profile.to_dict()
        success = True
        message = None
    except Exception as error:
        success = False
        user = target
        try:
            message = error.message
        except:
            message = 'Uncaught error. Check terminal logs'
    client.disconnect()

    
    with open(f'{output}/{timestamp}-{target}-follow.json', 'w') as file:
        json.dump({'timestamp': timestamp, 'action': 'follow', 'success': success, 'target': user, 'message': message}, file)

    if success:
        click.secho(f"The user {target} has been followed. Response can be found in {output}/{timestamp}-{target}-follow.json", fg='green')
    else:
        click.secho(f"An exception was raised when following the user {target}. Response can be found in {output}/{timestamp}-{target}-follow.json", fg='red')



@instacli.command()
@click.option('--login', type=click.STRING, help='The instagram username to use for the scrape.', required=True)
@click.option('--password', type=click.STRING, hide_input=True, help="The password of the IG account you are using for the scrape.", required=True)
@click.option('--target', required=True, type=click.STRING, help="The username of the user to scrape.")
@click.option('--output', type=click.Path(exists=True, dir_okay=True), help="The path to the folder where you wish the JSON output to be saved to.")
def unfollow(login, password, target, output):
    """Unfollow a specified user
    
    The response of this action will be saved in a dedicated JSON file in the 
    specified output folder.

    The output will be saved in a .json file inside the folder specified by ``--output``.
    The naming of the .json file will be consistent with the following format:
    ``timestamp-target-action.json``, where ``timestamp`` is the timestamp of the launch
    of the command, ``target`` is the user you are getting info on and ``action`` will be ``unfollow``.
    """
    if not chromedriver():
        return

    timestamp = int(time.time())
    settings = Settings()
    if not settings.driver_path:
        click.echo("No path for the chromedriver defined. Please define it using: instacli settings -dp [...]")
        return

    if not output and not settings.output_path:
        click.echo("No output specified in command nor in settings. Please specify it with --output")
        return

    if not output:
        output = settings.output_path

    client = IGClient()
    client.login(login, password)
    try:
        profile = client.get_profile(target)
        if not profile:
            raise InvalidUserError(target)
        profile.unfollow()
        user = profile.to_dict()
        success = True
        message = None
    except Exception as error:
        success = False
        user = target
        try:
            message = error.message
        except:
            message = 'Uncaught error. Check terminal logs'
    client.disconnect()

    
    with open(f'{output}/{timestamp}-{target}-unfollow.json', 'w') as file:
        json.dump({'timestamp': timestamp, 'action': 'unfollow', 'success': success, 'target': user, 'message': message}, file)

    if success:
        click.secho(f"The user {target} has been unfollowed. Response can be found in {output}/{timestamp}-{target}-unfollow.json", fg='green')
    else:
        click.secho(f"An exception was raised when unfollowing the user {target}. Response can be found in {output}/{timestamp}-{target}-unfollow.json", fg='red')


if __name__ == '__name__':
    instacli(prog_name='instacli')

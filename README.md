# Twitter friends CSV export/import

Utility program for exporting the list of profiles a Twitter user is following into a local CSV file. 
That CSV file can then be used to import the followees (known as "*friends*") into another Twitter account. 

This program uses the [Twython](https://twython.readthedocs.io) Python wrapper for the 
[Twitter API](https://developer.twitter.com/en/docs).

This utility tries to stick to the Twitter [limits](https://developer.twitter.com/en/docs/twitter-api/v1/rate-limits) 
around volume and frequency of API requests and limitations around following 
[too many new users too quickly](http://support.twitter.com/articles/66885-i-can-t-follow-people-follow-limits).   

## Usage

### Application environment config

The file `dot_env.example` serves as an example for a `.env` file that must be created and populated with the same
variables. `.env` is environment-specific and shouldn't be included in source control. It  contains a few variables 
values that can be changed to modify the application's behavior. 

Those vars are concerned with customizing logging behavior (log file location & name, log level) as well as 
specifying the data directories where the program will create / look for CSV files to export or import.

Configuration variables examples:
```
APP_LOG_DIR=./logs/
APP_LOG_FILENAME=application.log
LOG_LEVEL=INFO
EXP_DATA_DIR=./data/export
IMP_DATA_DIR=./data/import
```  

### Authentication

To use the exporter/importer a user needs to have been authenticated into Twitter and have authorized a 3rd party app
with the required Twitter access level.

So, a pre-authorized [Twitter 3rd party app](https://developer.twitter.com/en/docs/apps/overview) is 
required to run this application.  

When the 3rd party app is setup, it's given a key and a secret that are required to be included in any request
sent to the Twitter API. This application expects those two pieces of information being set as OS environment
variables with the names:
  - `TW_FRNDS_EI_APP_KEY`
  - `TW_FRNDS_EI_APP_SECRET`

Relevant Twitter docs 
[here](https://developer.twitter.com/en/docs/authentication/oauth-1-0a/obtaining-user-access-tokens).

Once the 3rd party app is setup the user can then authenticate into Twitter and authorize the app to perform
Twitter requests in their name. Once that is done, the user is given a permanent access token and secret token 
([OAuth tokens](https://www.oauth.com/oauth2-servers/access-tokens/)) that are used for authenticating 
requests sent to the Twitter API within the realm of the 3rd party app. 

### Exporting

```
python -m tw_frnds_ei.main_exporter [TW_OAUTH_USER_TOKEN] [TW_OAUTH_USER_TOKEN_SECRET] 
``` 
where:
 - `TW_OAUTH_USER_TOKEN` is the OAuth token provided by Twitter 
 - `TW_OAUTH_USER_TOKEN_SECRET` is the OAuth secret provided by Twitter

If the exporting process is successful a CSV file is generated containing user screen names and ids of
the authenticated user's friends (Twitter profiles the user follows). The CSV file location is shown 
in the output on finalization.


### Importing

```
python -m tw_frnds_ei.main_importer [TW_OAUTH_USER_TOKEN] [TW_OAUTH_USER_TOKEN_SECRET] [CSV_FILE_NAME] 
``` 
where:
 - `TW_OAUTH_USER_TOKEN` is the OAuth token provided by Twitter 
 - `TW_OAUTH_USER_TOKEN_SECRET` is the OAuth secret provided by Twitter
 - `CSV_FILE_NAME` is the file to be imported - It must be present in the directory: `./data/import`

The import process can be partially successful, at a given moment a request for following a user
can fail without possibility of retries. In that case the process is aborted and the Twitter
profiles that were successfully followed are reported in the program's output.

## App limits

The maximum number of friendships that the program can export or import is **3000**

## Throttler

When importing friendships the application spreads out the requests to follow profiles so that there are no more than
400 friendship requests per day, to respect Twitter's
 [rules](https://help.twitter.com/en/using-twitter/twitter-follow-limit) around that. The "*per day*" limitation
 is understood as "*within a sliding 24h window*".   

## Sleep & Retry on error

When exporting friends, depending on the number of friendship download requests (friends *data pages* 
being requested to Twitter) Twitter may respond with an error about the API's rate of requests having been 
exceeded. 

When importing, each row in the CSV file generates a *follow request* that's sent to 
Twitter's API. Twitter may respond with a rate error at any given time, depending on the number
of requests that were sent within certain
 [time frames](https://developer.twitter.com/en/docs/twitter-api/v1/rate-limits) (even with the implemented
 throttling).  

In any case any API request may produce an error for connectivity or system failure issues.

The program has some logic around those types of errors to put the whole process in *sleep mode* for whatever 
time is considered necessary, in order to try to resume the process automatically at the same point it
had been paused. That waiting time (during which there is practically no waste of CPU cycles or network activity) 
can be quite long, sometimes as long as **24h**.   


## Logs

While the program is running it reports the steps it's executing to the application's log file. 
The user can monitor the steps by tailing the logs: `tail -f [LOG_FILE]` 


## Data dirs and CSV files

The progam uses predefined directories as fixed locations for CSV files. Those directories must be specified in the
`.env` file. Example:
 
```
EXP_DATA_DIR=./data/export
IMP_DATA_DIR=./data/import
```

When exporting, the program creates the file name automatically using this pattern: 
```
friends_[TWITTER_USER_NAME]_[TIMESTAMP].csv
```
where:
 - `TWITTER_USER_NAME` is user name of the Twitter authenticated user that the program is running for. 
 - `TIMESTAMP` a timestamp of the moment the file was created, to force new files being created at each run.

When importing, the user can specify any file name. That file should be present in the predefined import data directory.

## Unit tests

[pytest](https://pytest.org) is used for that. The test scripts live in the same directory as 
the project's `.py` source files, in the `tests` subdir. The tests create a *mock* `twython.Twython` 
object to customize it according to the scenarios being tested. 

Tests leave a trace behind: they log activitiy in `./logs/pytest.log` and they generate fake 
exported CSV files in `tests/data/export` directory. 


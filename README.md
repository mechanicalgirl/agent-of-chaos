# agent-of-chaos

`chaosagent.py` is an agent designed to crawl a server, document its processes and services, and prepare a report highlighting vulnerabilities and critical issues.

The agent uses only three tools:
- Running read-only shell commands on the remote server via SSH (with specific exclusions for dangerous commands)
- Reading the contents of a file on the remote server
- Downloading a text file from the remote server to local storage for detailed review

Before running the agent, you'll need to set SSH values and an ANTHROPIC_API_KEY in a local .env file (see .env.example).

Currently, the agent is directed to analyze an example email server, but can be targeted differently with adjustments to its prompt language. As a standalone application, it's built to be run with `uv`.

```
uv run chaosagent.py
```

Note that the agent:
- Does not exhaustively ls every directory
- Prioritizes named/config files over empty directories

As it runs, it will log out its progress as it moves through the targeted system. That log output, along with a final report, plus any files retrieved from the server, will be stored in a local `session-{timestamp}` folder (see `example-session/`).

---

## Testing the agent

Before testing the agent, you'll need:

- an ANTHROPIC_API_KEY

- configured .env

- Docker installed and running locally

To test the agent's accuracy and fine-tune the prompt, I'm using:

- Dockerfiles based on different versions of Ubuntu (one on a current version, and one using Ubuntu 14, the oldest available on Dockerhub)

- A build.sh script that randomly selects one of the Dockerfiles and executes Docker build/run commands

- A setup.sh script, invoked at build time, that generates additional system elements based on a CHAOS level of `low`, `medium` or `high`.

Each of the Dockerfiles:

- Installs multiple services

- Creates a `crawler` user

- Sets SSH permissions

- Applies the setup.sh script to randomize other system elements

- Exposes port 22

Setup.sh:

- Generates manifests documenting what was installed (.txt for readability, and .json for programmatic evaluation)

- Places those manifest files in random locations for the agent to find and retrieve

- Based on a "CHAOS level" passed through the build command, may:

  - place text files at random locations around the system

  - create empty folders with import sounding names

  - start some services and leave others unstarted

  - create suspicious cron jobs

  - change permission levels on files

These differences are designed to generate a slightly different build each time, so that the agent is challenged to identify every misconfiguration and potential risk.

The testing workflow is:

```
./build.sh low[medium,high]       # build and run with a chaos level

uv run chaosagent.py              # run the agent and review its output
```

Note that If no CHAOS level is passed in, the setup.sh script will default to medium. Defaults are defined in both the Dockerfile:
```
ARG CHAOS_LEVEL=medium
```

And in the setup.sh script for redundancy:
```
CHAOS_LEVEL=${1:-medium}
```


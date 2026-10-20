"""A Gemini agent (Google ADK) whose only tool runs code in a sandbox.
Switch where the code runs with SANDBOX_BACKEND=docker|gke in .env."""
import os

from google.adk.agents import Agent

from .backends import run_code as _run_code


def run_code(code: str) -> dict:
    """Runs a complete Python 3 program in an isolated sandbox and returns its
    stdout, stderr, exit code, which backend ran it, and how long it took.
    Use this for any calculation, data processing, or checking facts about
    the environment. The program must print its results."""
    return _run_code(code).as_dict()


root_agent = Agent(
    name="sandbox_agent",
    model=os.getenv("MODEL", "gemini-2.5-flash"),
    description="Answers questions by writing Python and running it in a sandbox.",
    instruction=(
        "You solve tasks by writing a complete Python 3 program and calling "
        "run_code. Use only the standard library. Always print results. "
        "After the tool returns, report the answer, then one line saying which "
        "backend ran the code and how many seconds it took."
    ),
    tools=[run_code],
)

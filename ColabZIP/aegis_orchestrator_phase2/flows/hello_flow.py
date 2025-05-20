"""Example Prefect flow to verify infrastructure."""

from prefect import flow, task


@task
def say_hello():
    print("Hello from Aegis Orchestrator MVP!")


@flow
def hello_flow():
    say_hello()


if __name__ == "__main__":
    hello_flow()

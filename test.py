from pulumi import automation as auto
import pulumi
from pulumi_github import get_repository


def program():
    r = get_repository(full_name="torvalds/linux")
    pulumi.export("name", r.name)


stack = auto.create_or_select_stack(
    stack_name="dev",
    project_name="inline-demo",
    program=program,  # 不需要显式 LocalWorkspace
)
result = stack.up()
print(result.outputs["name"].value)

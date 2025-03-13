# ECS Exec

This [Tampermonkey](https://www.tampermonkey.net/) user script adds a shortcut to the Session Manager.

Currently, AWS does not support accessing containers from the web console like EC2. However, you can access a container via the Session Manager:

![Session Manager](session-manager.png)

Because the `aws ssm start-session` command's `--target` parameter [can also take a value in the format `ecs:<cluster-name>_<task-id>_<container-runtime-id>`](https://stackoverflow.com/a/67641633), we can use it to access containers from the web.

This script attaches a link to the Session Manager in the **Container name** column.

![ECS Console](ecs-console.png)

To access the container, ECS Exec should be configured. If it is not configured, please refer to [the official documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html).

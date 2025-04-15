# DBeaver

Example usage of the `session-manager` command to automate [DBeaver](https://dbeaver.io/) connections through Session Manager.

1. Install the **aws-annoying** CLI. Here, we use [pipx](https://github.com/pypa/pipx):

    ```shell
    pipx install aws-annoying
    ```

2. Run DBeaver. Since DBeaver, by default, runs scripts in a non-login shell, environment variables may need to be forwarded.

    Below is a macOS-specific example for running DBeaver with user environment variables:

    ```shell
    export && open -a 'DBeaver'
    ```

    You can save this command in a `.command` file for convenience. Optionally, specify the AWS profile to use:

    ```shell
    export && AWS_DEFAULT_PROFILE=mfa open -a 'DBeaver'
    ```

3. Create a new connection:

    ![New Connection](./new-connection.png)

4. Update the **Before Connect** script:

    ![Before Connect](./before-connect.png)

    ```shell
    aws-annoying session-manager port-forward --local-port ${port} --through "<EC2 instance name or ID>" --remote-host "<Database hostname>" --remote-port "<Database port>" --pid-file /tmp/dbeaver-${port}.pid --terminate-running-process --log-file /tmp/dbeaver-${port}.log
    ```

    Update `--through`, `--remote-host`, and `--remote-port` as needed, based on your infrastructure and database engine. Additionally, the **Pause after execute (ms)** setting may need adjustment based on your network conditions.

5. Update the **After Disconnect** script:

    ![After Disconnect](./after-disconnect.png)

    ```shell
    aws-annoying session-manager stop --pid-file /tmp/dbeaver-${port}.pid
    ```

6. Run **Test Connection ...** to verify the setup.

    ![Test Connection](./test-connection.png)

# File Browser S3 access

![File Browser S3 access](webui/thumbnail.webp)

S3 buckets and key prefixes with explicit credentials and conditional object writes.

## Compatibility

**Preview: requires Agent Zero's new File Browser connection provider interface, version 1 (`helpers.file_connections.API_VERSION`).** This interface is currently under development; existing Agent Zero releases without it are not supported. The Plugin Index submission is a draft until that core interface ships. Installing the plugin alone does not upgrade Agent Zero.

## Install and configure

Install this repository through Agent Zero's Plugin Hub Git URL installer. Enable the plugin globally, then open its settings and choose **Open connection settings**, or use **Files → Settings → Add connection** and select this transport.

Enter a bucket, region, optional key prefix, access key ID and secret access key. Temporary credentials may include a session token. Leave endpoint empty for AWS or enter a verified HTTPS S3-compatible endpoint. Credentials must grant only the desired bucket/prefix operations; no ambient instance credentials are used.

Dependencies: boto3 1.43.36. The installer calls `hooks.py install()` in the Agent Zero framework runtime. It is safe to rerun; there is no execute.py.

## Use and permissions

Save a named connection, test it, then use the folder icon in the connection list. Each connection has independent Browse, Download, Upload/create, Edit, Rename/move and Delete controls; unsupported actions are disabled. Browse and Download default on; mutations default off. Text and code files open in the shared Editor. Files supports list/icon views and the optional file tree for remote connections.

Permissions constrain File Browser operations, not arbitrary agent shell tools or server accounts. Editing necessarily reveals file content. Credentials are stored privately (0600) under this plugin's `data/connections.json` and are omitted from browser responses. An unchanged secret retains its saved value; replacing it updates it. Protect the instance and its backups.

## Limits

Folders are prefixes and empty-folder markers, not POSIX directories. Rename/move is deliberately unavailable because S3 lacks atomic rename. Conditional puts must be supported by a compatible endpoint. Deleting a versioned object creates a delete marker; this plugin does not purge old versions. Object and prefix names that collide cannot be represented independently in the file-browser view. Browsing and requests may incur provider charges.

Shared Files limits: 100 MiB uploads/download archives, 1000 archive entries, nesting depth 64; Editor supports UTF-8 nonbinary files up to 1 MiB. Cross-connection moves and remote-to-local Save As are not supported. Use download/upload to transfer between connection types. Internet access to the configured server is required; storage/network charges remain your provider's responsibility.

## Verification

Botocore Stubber checks verify bucket/prefix requests and If-None-Match/If-Match writes, including failed preconditions. Run `python -m unittest -v test_transport` from the repository with the framework interpreter. No paid cloud account or actual object store was used in automated validation.

Before production use, test a disposable folder on your actual server: listing, new upload, Editor save, duplicate destination rejection, stale-save rejection, download, rename where supported, and deletion. Confirm denied actions remain denied and disable the plugin to confirm connections become unavailable. Protocol differences and server permissions matter.

## Disable and remove

Disabling hides this provider and rejects further connection operations. Removing a connection deletes its saved credentials. Uninstalling deletes the plugin directory, including saved connections and any plugin-owned key; back up what you need first. Shared Python dependencies are not uninstalled because other plugins may use them. No service, mount or system symlink is created. Legacy SSH data is preserved during migration and is not removed by uninstall.

## License

MIT. See [LICENSE](LICENSE). Agent Zero-derived integration retains its upstream license notice.

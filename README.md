# exteraGram test plugin repository

A test repository for the exteraGram plugin catalog. It follows the
plugin repository format from the plugin docs (Plugin Repositories).

Add it in exteraGram: **Plugins → Catalog → Repositories → Add → Git Repository**, then paste
the repository URL.

After changing a plugin file, run `python3 build_index.py` and commit `extera-plugins.json`,
or let the GitHub Actions workflow do it on push.

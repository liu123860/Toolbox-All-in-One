# Privacy policy

Applies to the open-source distribution of Toolbox All-in-One.

## Data stored on your device

- Account and preference data are stored locally in a SQLite database under the
  current user's application data directory (`%APPDATA%`). No account is required
  to use the utilities.
- Passwords are never stored in plain text; they are stored as salted PBKDF2
  hashes.
- AI assistant API keys, if the user chooses to configure one, are encrypted
  with Windows DPAPI and kept on the local device only.

## Network access (only on explicit user action)

- **Weather tool**: on user request, queries a public weather endpoint
  (Open-Meteo, with wttr.in as fallback) using the city or coordinates the user
  entered. No device identifiers are sent. Results are cached locally for
  offline use.
- **AI assistant**: only if the user configures an endpoint and key, and only
  when the user sends a message. The content the user typed is sent to the
  endpoint the user chose.
- **Browser tool**: loads the pages the user navigates to, like any browser.

There is **no telemetry, no analytics, no advertising network, no crash
reporting, and no background upload**. The open-source build contains no
advertising and no paid tiers.

## Installation and system changes

- The installer writes only to a directory chosen by the user (default: under
  the current user's profile). It does not require administrator privileges,
  does not write to the system registry's machine-wide areas, and does not
  install services or drivers.
- The installer displays this privacy policy before installation and offers an
  option to disable all networked features.
- The portable ZIP requires no installation; delete its folder to uninstall.

## Uninstallation

- Installed version: run `卸载.bat` (uninstall.bat) in the installation folder,
  or delete the folder. The uninstaller only removes directories it created
  itself (identified by an installation marker) and refuses any other path.
- Local user data under `%APPDATA%` is left in place so the user can keep
  settings; delete it manually if desired.

## Third parties

Third-party libraries and their licenses are listed in the repository. This
project does not bundle proprietary components. Weather endpoints have their own
privacy policies that apply when the user invokes that tool.

## Contact

Open an issue in this repository. Changes to this policy are published in the
repository history.

# Security Policy

## Supported Versions

Security fixes are provided for the latest release line only:

| Version              | Supported          |
| -------------------- | ------------------ |
| 5.0.x (unreleased)   | :construction: in development |
| 4.4.x                | :white_check_mark: |
| < 4.4                | :x:                |

Please upgrade to the latest release before reporting an issue, and check
whether it is still reproducible.

Code in `wsgidav/samples/` (sample providers, the impersonator middleware,
etc.) is example code. It is not guaranteed to work correctly or securely
and is not covered by this policy.


## Reporting a Vulnerability

Thank you for reporting a security related issue using a private channel
instead of opening a public issue!

The security team (i.e. me) will try to acknowledge and respond as quickly as
possible.

To report a security issue, please email 

> security(at)wwwendt.de

and, to your best knowledge, please

- Include your name and affiliation (if any).
- Include the scope of the vulnerability. Let us know who could use this exploit.
- Mention the affected versions.
- Document steps to identify the vulnerability. It is important that we can 
  reproduce your findings.
- Describe how to exploit vulnerability, give us an attack scenario.
- If known, describe mitigations for the issue.

This project follows a 90 day disclosure timeline.

(See also [Vulnerability Disclosure Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Vulnerability_Disclosure_Cheat_Sheet.html#initial-report).)

# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in PySIBS, please **do not open a public
issue**. Instead, report it privately via GitHub's
[private vulnerability reporting](https://github.com/robertruben98/pysibs/security/advisories/new)
or by emailing the maintainer. We will acknowledge your report as soon as possible and
keep you informed about the fix.

Please include enough detail to reproduce the issue (affected version, steps, and
impact).

## Supported versions

PySIBS is in alpha. Security fixes are applied to the latest released version.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | ✅        |

## Handling of sensitive data

PySIBS is designed to minimise exposure of sensitive data:

- It does **not** store or process PAN, CVV or other cardholder data itself.
- It never logs `Authorization` headers, API keys or webhook secrets.
- Exceptions never include the request payload or credentials.
- No examples or tests contain real card numbers or credentials.

### PCI DSS

Some SIBS server-to-server card payment flows may bring the merchant environment into
PCI DSS scope. Using this SDK does not by itself make an integration PCI compliant.
Always validate your integration scope with SIBS and your PCI advisor.
